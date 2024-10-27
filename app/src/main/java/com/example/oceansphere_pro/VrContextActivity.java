package com.example.oceansphere_pro;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.ImageView;

import androidx.annotation.Nullable;

import com.example.oceansphere_pro.BaseActivity;
import com.example.oceansphere_pro.R;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.List;
import java.util.concurrent.BlockingQueue;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;



public class VrContextActivity extends BaseActivity implements GLSurfaceView.Renderer,SensorEventListener {
    private static final String IP_ADDRESS = "192.168.10.103"; // 替换为目标IP地址
    private static final int PORT = 8765; // 替换为目标端口

    private GLSurfaceView mGLView;
    private SensorManager mSensorManager;
    private Sensor mRotation;
    private SkySphere mSkySphere;
    private Handler handler2;
    private boolean isSending = false;
    private int[] currentState = {0, 0, 0};
    private Runnable sendRunnable;
    private Handler handler = new Handler();
    private float[] matrix=new float[16];
    private UdpReceiver udpReceiver;
    public Bitmap mBitmap ;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.glview);

        mSensorManager=(SensorManager)getSystemService(Context.SENSOR_SERVICE);
        List<Sensor> sensors=mSensorManager.getSensorList(Sensor.TYPE_ALL);
        //todo 判断是否存在rotation vector sensor
        mRotation=mSensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);

        mGLView=(GLSurfaceView) findViewById(R.id.mGLView);
        mGLView.setEGLContextClientVersion(2);
        mGLView.setRenderer(this);
        mGLView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);

        mSkySphere=new SkySphere(this.getApplicationContext(),"360sp.jpg");

        handler2 = new Handler(Looper.getMainLooper());
        udpReceiver = new UdpReceiver(8081);
        Thread receiverThread = new Thread(udpReceiver);
        receiverThread.start();

        BlockingQueue<byte[]> imageQueue = udpReceiver.getImageQueue();
        setupButton(R.id.mButtonForward, 0, 1);
        setupButton(R.id.mButtonBehind, 0, 2);
        setupButton(R.id.mButtonLeft, 1, 1);
        setupButton(R.id.mButtonRight, 1, 2);
        setupButton(R.id.mButtonUp, 2, 1);
        setupButton(R.id.mButtonDown, 2, 2);


        new Thread(() -> {
            while (true) {
                try {
                    byte[] imageData = imageQueue.take();
                    handler2.post(() -> updateImageView(imageData));
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        }).start();

    }



    @Override
    protected void onResume() {
        super.onResume();
        mSensorManager.registerListener(this,mRotation,SensorManager.SENSOR_DELAY_GAME);
        mGLView.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        mSensorManager.unregisterListener(this);
        mGLView.onPause();
    }

    @Override
    public void onSurfaceCreated(GL10 gl, EGLConfig config) {
        mSkySphere.create();
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glEnable(GLES20.GL_CULL_FACE);
        GLES20.glCullFace(GLES20.GL_FRONT);
    }

    @Override
    public void onSurfaceChanged(GL10 gl, int width, int height) {
        mSkySphere.setSize(width, height);
        GLES20.glViewport(0,0,width,height);
    }

    @Override
    public void onDrawFrame(GL10 gl) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT|GLES20.GL_DEPTH_BUFFER_BIT);
        GLES20.glClearColor(1,1,1,1);
        mSkySphere.draw();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        SensorManager.getRotationMatrixFromVector(matrix,event.values);
        mSkySphere.setMatrix(matrix);
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {

    }


    private void updateImageView(byte[] imageData) {
        Bitmap bitmap = BitmapFactory.decodeByteArray(imageData, 0, imageData.length);
        if (bitmap != null) {
            runOnUiThread(() -> {
                mSkySphere.updateTexture(bitmap);
                if (mSkySphere.textureId != 0) {
                    mGLView.requestRender(); // 请求重新渲染
                    Log.i("VrContextActivity", "纹理已更新，ID：" + mSkySphere.textureId);
                } else {
                    Log.e("VrContextActivity", "更新纹理失败，ID为0");
                }
            });
        } else {
            Log.e("VrContextActivity", "Bitmap 解码失败");
        }
    }



    private void setupButton(int buttonId, final int index, final int value) {
        Button button = findViewById(buttonId);
        button.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        currentState[index] = value;
                        isSending = true;
                        startSending();
                        break;
                    case MotionEvent.ACTION_UP:
                    case MotionEvent.ACTION_CANCEL:
                        currentState[index] = 0;
                        if (noButtonsPressed()) {
                            sendUdpData("000");
                            isSending = false;
                            handler.removeCallbacks(sendRunnable);
                        }
                        break;
                }
                return true;
            }
        });
    }

    private boolean noButtonsPressed() {
        for (int value : currentState) {
            if (value != 0) {
                return false;
            }
        }
        return true;
    }

    private void startSending() {
        sendRunnable = new Runnable() {
            @Override
            public void run() {
                if (isSending) {
                    sendUdpData(formatState());
                    handler.postDelayed(this, 10); // 0.01秒间隔
                }
            }
        };
        handler.post(sendRunnable);
    }

    private String formatState() {
        StringBuilder sb = new StringBuilder();
        for (int value : currentState) {
            sb.append(value);
        }
        return sb.toString();
    }

    private void sendUdpData(final String message) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    DatagramSocket socket = new DatagramSocket();
                    InetAddress address = InetAddress.getByName(IP_ADDRESS);
                    byte[] buffer = message.getBytes();
                    DatagramPacket packet = new DatagramPacket(buffer, buffer.length, address, PORT);
                    socket.send(packet);
                    socket.close();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // 如有需要，适当停止UDP接收器
        // udpReceiver.stop(); // 如有需要实现stop方法
    }

}