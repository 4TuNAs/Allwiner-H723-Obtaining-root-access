import serial
import threading
import time
import sys

PORT = "COM5"
BAUD = 115200

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=0.001,
    write_timeout=0.1,
    rtscts=False,
    dsrdtr=False
)

try:
    ser.dtr = False
    ser.rts = False
except:
    pass

stop = False
sboot_seen = False

def reader():
    global stop, sboot_seen

    buf = bytearray()

    while not stop:
        d = ser.read(4096)
        if not d:
            continue

        sys.stdout.buffer.write(d)
        sys.stdout.buffer.flush()

        buf.extend(d)
        if len(buf) > 8192:
            del buf[:-4096]

        if b"HELLO! SBOOT is starting!" in buf:
            sboot_seen = True

        if b"detected user input 2" in buf:
            print("\n\n*** INPUT 2 ACCEPTED ***")
            stop = True

        if b"U-Boot 2018.07" in buf:
            print("\n\n*** Too late: reached U-Boot ***")
            stop = True

threading.Thread(target=reader, daemon=True).start()

print("COM5 opened.")
print("Power-cycle board now.")
print("Waiting for SBOOT...")

# До появления SBOOT ничего не посылаем
while not sboot_seen and not stop:
    time.sleep(0.001)

if sboot_seen:
    print("\n*** SBOOT detected — sending '2' ***")

    t0 = time.perf_counter()

    # Долбим только короткое раннее окно boot0/SBOOT
    while time.perf_counter() - t0 < 0.50 and not stop:
        ser.write(b"2")
        ser.flush()
        time.sleep(0.001)

# Оставляем UART открытым ещё немного
t = time.time()
while time.time() - t < 5 and not stop:
    time.sleep(0.01)

time.sleep(1)
stop = True
ser.close()

print("\nCOM5 released.")