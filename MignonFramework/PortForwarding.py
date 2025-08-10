import socket
import threading
import select
import time

def _handle_client(client_socket, remote_host, remote_port, log_prefix, buffer_size):
    """
    （内部函数）为每个客户端连接创建一个处理器。
    它会连接到指定的远程服务器，并使用 select 在两个套接字之间双向转发数据。
    """
    remote_socket = None
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))
        print(f"{log_prefix} [+] 成功连接到远程服务器 {remote_host}:{remote_port}")

        while True:
            sockets_to_read = [client_socket, remote_socket]
            readable, _, _ = select.select(sockets_to_read, [], [])

            for sock in readable:
                try:
                    # 使用传入的 buffer_size 参数
                    data = sock.recv(buffer_size)
                    if not data:
                        print(f"{log_prefix} [-] 连接已由对端关闭。")
                        return

                    if sock is client_socket:
                        remote_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
                except ConnectionError:
                    print(f"{log_prefix} [-] 连接中断。")
                    return

    except ConnectionRefusedError:
        print(f"{log_prefix} [!] 无法连接到远程服务器 {remote_host}:{remote_port}。")
    except Exception as e:
        print(f"{log_prefix} [!] 转发过程中发生错误: {e}")
    finally:
        if client_socket:
            client_socket.close()
        if remote_socket:
            remote_socket.close()

def _start_listener(local_host, local_port, remote_host, remote_port, buffer_size):
    """
    （内部函数）为单个转发规则创建并启动一个监听服务。
    """
    log_prefix = f"[{local_port} -> {remote_port}]"
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((local_host, local_port))
        server_socket.listen(10)
        print(f"{log_prefix} [*] 端口转发服务已启动 (缓冲区: {buffer_size} bytes)，正在监听 {local_host}:{local_port} ...")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"\n{log_prefix} [+] 接收到来自 {addr[0]}:{addr[1]} 的新连接。")

            handler_thread = threading.Thread(
                target=_handle_client,
                # 将 buffer_size 传递给客户端处理器
                args=(client_socket, remote_host, remote_port, log_prefix, buffer_size)
            )
            handler_thread.start()

    except OSError as e:
        print(f"{log_prefix} [!] 启动监听失败: {e}")
    finally:
        server_socket.close()
        print(f"{log_prefix} [*] 监听服务已关闭。")

def start_services(port_mappings, buffer_size=40960):
    """
    启动所有端口转发服务。

    这是一个阻塞函数，它会一直运行直到被手动中断 (Ctrl+C)。

    :param port_mappings: 一个包含转发规则的列表。
                          每个元素都是一个字典，格式为:
                          {
                              'local_host': str,
                              'local_port': int,
                              'remote_host': str,
                              'remote_port': int
                          }
    :param buffer_size: 每次接收数据的缓冲区大小（字节），默认为 40960。
    """
    if not port_mappings:
        print("[!] 错误：端口转发表为空，无法启动服务。")
        return

    threads = []
    print(f"[*] 准备为 {len(port_mappings)} 条规则启动转发服务...")

    for mapping in port_mappings:
        thread = threading.Thread(
            target=_start_listener,
            # 将 buffer_size 传递给每个监听器
            args=(
                mapping['local_host'],
                mapping['local_port'],
                mapping['remote_host'],
                mapping['remote_port'],
                buffer_size
            ),
            daemon=True
        )
        threads.append(thread)
        thread.start()
        time.sleep(0.1)

    print("[*] 所有服务已启动。按 Ctrl+C 来关闭所有服务。")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[*] 收到关闭信号，正在关闭所有服务...")
    finally:
        print("[*] 服务器已成功关闭。")




