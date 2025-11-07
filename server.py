import socket
import time
import threading

clients = {}  # Dictionary to store connected clients

lock = threading.Lock()

def handle_client(client_socket, client_address):
    with lock:
        clients[client_address] = client_socket
    print(f"[+] {client_address} connected.")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(f"[{client_address}] {data.decode()}")
    except:
        pass
    finally:
        with lock:
            del clients[client_address]
        client_socket.close()
        print(f"[-] {client_address} disconnected.")


def con():
    try:

        ch = None
        while True:
            if ch == None:
                with lock:
                    if not clients:
                        print("[!] No clients connected.")
                        continue

                    print("\n[Clients Connected]")
                    for i, addr in enumerate(clients.keys()):
                        print(f"{i + 1}. {addr}")            
                # server_message = input(":")
                    try:
                        choice = int(input(" >"))
                        ch = choice
                    except:
                        continue
                    if choice == 0 :
                        continue
            else:
                choice = ch
            with lock:
                selected_addr = list(clients.keys())[choice - 1]
                client_socket_ = clients[selected_addr]
            server_message = input(f": ")
            if server_message =="":
                server_message = "cmd"
            if server_message =="idk":
                ch = None
                continue
            client_socket_.sendall(server_message.encode())
            
            # client_socket.send(server_message.encode())
            def getmsg():
                # server_message = client_socket.recv(1024).decode()
                if not server_message:
                    print("Server disconnected.")
                    return
                print(f"{server_message}")
            thread = threading.Thread(target = getmsg)
            thread.start()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        
        client_socket.close()
        server_socket.close()
def main():
    global server_socket
    SERVER_HOST = '0.0.0.0'  
    SERVER_PORT = 12345

    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    
    server_socket.bind((SERVER_HOST, SERVER_PORT))

    
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
    threading.Thread(target=con, daemon=True).start()

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection established with {client_address}")
        client_thread = threading.Thread(
            target=handle_client, args=(client_socket, client_address)
        )
        client_thread.daemon = True
        client_thread.start()

while True:
    try:
        main()
    except Exception as e:
        print(e)

