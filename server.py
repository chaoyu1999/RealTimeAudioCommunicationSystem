import asyncio
import pyaudio
import struct
import websockets
import collections
import json

DELAY_BUF_SIZE = 10  # 延迟抖动缓冲区大小
MAX_DELAY = 0.1  # 最大延迟值，超过这个值直接丢弃
CH_NUM = 1  # 电脑声道数


async def server(websocket, path):
    print("Client connected")
    # 初始化延迟抖动缓冲区
    delay_buf = collections.deque(maxlen=DELAY_BUF_SIZE)
    for i in range(DELAY_BUF_SIZE):
        delay_buf.append(0)
    p = pyaudio.PyAudio()
    stream = None
    ch = None
    while True:
        try:
            data = await websocket.recv()
            if not data:
                break
            if stream:
                audio = struct.unpack("%df" % (len(data) / 4), data)
                res = []
                for i in range(len(audio)):
                    tem = [0.0 for j in range(CH_NUM)]
                    for k in ch:
                        tem[int(k) - 1] = audio[i]
                    res.extend(tem)

                delay = (len(audio) / 11025)  # 计算延迟
                delay_buf.append(delay)  # 将延迟加入缓冲区
                avg_delay = sum(delay_buf) / DELAY_BUF_SIZE  # 计算平均延迟
                delay_diff = delay - avg_delay  # 计算延迟差
                if delay_diff > MAX_DELAY:
                    continue  # 延迟超过最大值，直接丢弃
                await asyncio.sleep(max(0, delay_diff))  # 异步等待延迟差
                await asyncio.get_running_loop().run_in_executor(None, stream.write, struct.pack("%df" % len(res),
                                                                                                 *res))  # 异步执行stream.write(data)
            if not stream:
                print(f"输出通道：{data}")
                ch = json.loads(data)['channels']
                stream = p.open(format=pyaudio.paFloat32,
                                channels=CH_NUM,
                                rate=11025,
                                output=True,
                                frames_per_buffer=4096)
        except websockets.exceptions.ConnectionClosed:
            break
    print("Client disconnected")
    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == '__main__':
    start_server = websockets.serve(server, "127.0.0.1", 7865)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
