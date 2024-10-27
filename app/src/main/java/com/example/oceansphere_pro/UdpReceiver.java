package com.example.oceansphere_pro;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

public class UdpReceiver implements Runnable {
    private final int port;
    private final BlockingQueue<byte[]> imageQueue;

    public UdpReceiver(int port) {
        this.port = port;
        this.imageQueue = new LinkedBlockingQueue<>();
    }

    @Override
    public void run() {
        DatagramSocket socket = null;
        try {
            socket = new DatagramSocket(port);
            byte[] buffer = new byte[1024 * 1024]; // Adjust buffer size as needed
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length);

            while (true) {
                socket.receive(packet);
                byte[] imageData = new byte[packet.getLength()];
                System.arraycopy(packet.getData(), 0, imageData, 0, packet.getLength());
                imageQueue.put(imageData);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (socket != null && !socket.isClosed()) {
                socket.close();
            }
        }
    }

    public BlockingQueue<byte[]> getImageQueue() {
        return imageQueue;
    }
}