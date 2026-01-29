import socket

HOST = "172.20.10.6"  # IP of the computer
PORT = 5050  # Port to send data

num = input("Enter a number (1-24): ")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(num.encode())
    print("Sent:", num)
