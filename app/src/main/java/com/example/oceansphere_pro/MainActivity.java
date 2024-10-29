package com.example.oceansphere_pro;

import java.util.ArrayList;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;

import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Collections;
import java.util.List;

public class MainActivity extends BaseActivity implements View.OnClickListener {

    private RecyclerView mList;
    private ArrayList<MenuBean> data;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        mList= (RecyclerView)findViewById(R.id.mList);
        mList.setLayoutManager(new LinearLayoutManager(this,LinearLayoutManager.VERTICAL,false));
        data = new ArrayList<>();
        add("点击启动", VrContextActivity.class, getIPAddress());


        mList.setAdapter(new MenuAdapter());
    }

    private void add(String name, Class<?> clazz, String ipAddress) {
        MenuBean bean = new MenuBean();
        bean.name = name;
        bean.clazz = clazz;
        bean.ipAddress = ipAddress;
        data.add(bean);
    }


    private static class MenuBean {
        String name;
        Class<?> clazz;
        String ipAddress;
    }


    private class MenuAdapter extends RecyclerView.Adapter<MenuAdapter.MenuHolder>{


        @Override
        public MenuHolder onCreateViewHolder(ViewGroup parent, int viewType) {
            return new MenuHolder(getLayoutInflater().inflate(R.layout.item_button,parent,false));
        }

        @Override
        public void onBindViewHolder(MenuHolder holder, int position) {
            holder.setPosition(position);
        }

        @Override
        public int getItemCount() {
            return data.size();
        }

        class MenuHolder extends RecyclerView.ViewHolder{

            private Button mBtn;

            MenuHolder(View itemView) {
                super(itemView);
                mBtn= itemView.findViewById(R.id.mBtn);
                mBtn.setOnClickListener(MainActivity.this);
            }

            public void setPosition(int position){
                MenuBean bean=data.get(position);
                mBtn.setText(bean.name);
                mBtn.setTag(position);
            }
        }

    }

    @Override
    public void onClick(View view) {
        int position = (int) view.getTag();
        MenuBean bean = data.get(position);

        // 发送数据
        sendIP(bean.ipAddress, "192.168.10.100", 8000, () -> {
            // 发送完成后跳转到新页面
            startActivity(new Intent(this, bean.clazz));
        });
    }


    private void sendIP(String ipAddress, String serverIP, int serverPort, Runnable callback) {
        new Thread(() -> {
            try {
                DatagramSocket socket = new DatagramSocket();
                InetAddress address = InetAddress.getByName(serverIP);
                byte[] buf = ipAddress.getBytes();
                DatagramPacket packet = new DatagramPacket(buf, buf.length, address, serverPort);
                socket.send(packet);
                socket.close();
                // 调用回调函数
                runOnUiThread(callback);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private String getIPAddress() {
        try {
            for (NetworkInterface intf : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                for (InetAddress addr : Collections.list(intf.getInetAddresses())) {
                    if (!addr.isLoopbackAddress()) {
                        String sAddr = addr.getHostAddress();
                        boolean isIPv4 = sAddr.indexOf(':') < 0;
                        if (isIPv4) return sAddr;
                    }
                }
            }
        } catch (Exception ex) {
            ex.printStackTrace();
        }
        return "";
    }


}