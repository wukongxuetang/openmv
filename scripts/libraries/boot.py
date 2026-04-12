import sensor, time
from machine import LED, Pin
from pyb import USB_VCP, UART
image_requested = 0
keyValue = 0
debug = False
redLed = LED("LED_RED")
greenLed = LED("LED_GREEN")
blueLed = LED("LED_BLUE")
CONFIG_FILE = "/flash/config.txt"
current_config = {'threshold':'180', 'exposure':'30','gain':'32','invert':'255',
'min':'5','max':'20000','xflip':'1','yflip':'1','id':'9'}
def safe_int(value, default=1):
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
        if value.lower() in ['true', 'yes', 'on']:
            return 1
        if value.lower() in ['false', 'no', 'off']:
            return 0
    if isinstance(value, bool):
        return 1 if value else 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
def load_config():
    try:
        config = {}
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        if debug:
            print("Loaded config:", config)
        return config
    except:
        save_config(current_config)
        return current_config
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    if debug:
        print("saved config:", current_config)
current_config = load_config()
exposure = int(current_config.get('exposure', 30))
threshold = int(current_config.get('threshold', 150))
minblob = int(current_config.get('min',100))
maxblob = int(current_config.get('max',2500))
gain = int(current_config.get('gain',32))
fanzhuan = int(current_config.get('invert',255))
xflip = safe_int(current_config.get('xflip'), 1)
yflip = safe_int(current_config.get('yflip'), 1)
gunId = int(current_config.get('id',9))
pin0 = Pin("P9", Pin.IN, Pin.PULL_UP)
pin1 = Pin("P1", Pin.IN, Pin.PULL_UP)
pin2 = Pin("P6", Pin.IN, Pin.PULL_UP)
pin3 = Pin("P3", Pin.IN, Pin.PULL_UP)
pin4 = Pin("P8", Pin.IN, Pin.PULL_UP)
pin5 = Pin("P7", Pin.IN, Pin.PULL_UP)
pin6 = Pin("P0", Pin.IN, Pin.PULL_UP)
pin7 = Pin("P2", Pin.IN, Pin.PULL_UP)
def get_button_state():
    key_state = 0
    if pin0.value() == 0: key_state |= 0x01
    if pin1.value() == 0: key_state |= 0x02
    if pin2.value() == 0: key_state |= 0x04
    if pin3.value() == 0: key_state |= 0x08
    if pin4.value() == 0: key_state |= 0x10
    if pin5.value() == 0: key_state |= 0x20
    if pin6.value() == 0: key_state |= 0x40
    if pin7.value() == 0: key_state |= 0x80
    return key_state
usb = USB_VCP()
uart = UART(3, 115200)
uart.init(115200, bits=8, parity=None, stop=1, flow=0)
sensorMode = sensor.GRAYSCALE
sensor.reset()
sensor.set_pixformat(sensorMode)
sensor.set_framesize(sensor.QVGA)
sensor.set_framebuffers(2)
sensor.skip_frames(time=200)
sensor.set_auto_whitebal(False, rgb_gain_db = (0.0, 0.0, 0.0))
sensor.set_brightness(-3)
sensor.set_auto_gain(False, gain_db=gain)
sensor.set_contrast(3)
sensor.set_saturation(1)
sensor.set_gainceiling(32)
sensor.set_quality(80)
def update_camera_settings():
    sensor.set_hmirror(xflip)
    sensor.set_vflip(yflip)
    sensor.set_auto_exposure(False, exposure_us=exposure)
update_camera_settings()
camWidth = sensor.width()
camHeight = sensor.height()
fontScale = camWidth / 320
clock = time.clock()
def find_light_spots(img):
    blobs = img.find_blobs([(threshold, 255)],
                          area_threshold=minblob,
                          merge=True,
                          margin=2
                          )
    lastBlobs = []
    for blob in blobs:
        if (blob.area() < maxblob):
            if blob.roundness() > 0.4 and blob.density() > 0.5:
                lastBlobs.append(blob)
    detected = []
    if len(lastBlobs) >= 1:
        lastBlobs.sort(key=lambda b: b.area(), reverse=True)
        detected = [(b.cx(), b.cy()) for b in lastBlobs[:min(2, len(lastBlobs))]]
    return detected
def show_debug_info(img, spots):
    img.draw_string(5, 5, f"blob Num {len(spots)}", color=255, scale=fontScale)
    if len(spots) == 0:
        return
    colors = [255, 200]
    for i, (u, v) in enumerate(spots):
        img.draw_circle(int(u), int(v), 6, color=colors[i])
        img.draw_string(int(u)+5, int(v)-20, f"P{i}", color=255)
        img.draw_string(5, 20+15*i, f"P{i}: ({spots[i][0]}, {spots[i][1]})", color=200, scale=fontScale)
    if len(spots) == 2:
        img.draw_line(int(spots[0][0]), int(spots[0][1]),int(spots[1][0]), int(spots[1][1]), color=180)
        center_u = int((spots[0][0] + spots[1][0]) / 2)
        center_v = int((spots[0][1] + spots[1][1]) / 2)
        img.draw_cross(center_u, center_v, color=150, size=8)
def process_command(cmd, isUsb):
    global exposure, xflip, yflip, image_requested, gunId
    if debug:
        print(f"command is:{cmd} isusb:{isUsb} set:{cmd.startswith("set")}")
    if cmd.startswith("set"):
        parts = cmd[3:].split(',')
        exposure = max(10, min(10000, int(parts[0])))
        update_camera_settings()
        current_config["exposure"] = exposure
        xflip = int(parts[1])
        yflip = int(parts[2])
        update_camera_settings()
        current_config["xflip"] = xflip
        current_config["yflip"] = yflip
        if debug:
            print(f"set from command {parts[0]} {parts[1]} {parts[2]}")
        save_config(current_config)
    elif cmd.startswith("capture"):
        if isUsb==1:
            image_requested = 1
        else:
            image_requested = 2
        if debug:
            print(f"capture from {isUsb}")
    elif cmd.startswith("id"):
        gunId = int(cmd[2:])
        if isUsb==0:
            settings = "I:%d\n" % (gunId)
            uart.write(settings.encode())
        current_config["id"] = gunId
        if debug:
            print(f"gun id is {gunId}")
        save_config(current_config)
    elif cmd.startswith("get"):
        settings = "S:%d,%d,%d\n" % (exposure, xflip, yflip)
        if isUsb==1:
            usb.send(settings.encode())
        else:
            uart.write(settings.encode())
            if debug:
                print(f"sent2esp:{settings.encode()},from:{isUsb}")
def send_image(img):
    global image_requested
    if image_requested==0:
        return
    img_compressed = img.compress( x_scale=0.5, y_scale=0.5,quality=25)
    img_len = len(img_compressed)
    if image_requested==2:
        uart.write(bytearray([0xAA, 0x55]))
        uart.write(img_len.to_bytes(4, 'little'))
        uart.write(img_compressed)
        uart.write(bytearray([0x55, 0xAA]))
    elif image_requested==1:
        usb.send(bytearray([0xAA, 0x55]))
        usb.send(img_len.to_bytes(4, 'little'))
        usb.send(img_compressed)
        usb.send(bytearray([0x55, 0xAA]))
    image_requested = 0
    if debug:
        print("img has sent", img_len, "bytes")
try:
    while True:
        if debug:
            clock.tick()
        keyValue = get_button_state()
        img = sensor.snapshot()
        spots = find_light_spots(img)
        if debug:
            show_debug_info(img, spots)
        if len(spots) == 2:
            redLed.off()
            greenLed.on()
            blueLed.off()
            data_str = "%d,%d,%d,%d,%d\n" % (spots[0][0], spots[0][1], spots[1][0], spots[1][1],keyValue)
            uart.write(data_str.encode())
            if not debug:
                print(f"{gunId},{spots[0][0]},{spots[0][1]},{spots[1][0]},{spots[1][1]},{keyValue}")
        elif len(spots) == 1:
            redLed.off()
            greenLed.off()
            blueLed.on()
            data_str = "%d,%d,%d,%d,%d\n" % (spots[0][0], spots[0][1], -1, -1, keyValue)
            uart.write(data_str.encode())
            if not debug:
                print(f"{gunId},{spots[0][0]},{spots[0][1]},-1,-1,{keyValue}")
        else:
            redLed.on()
            greenLed.off()
            blueLed.off()
            data_str = "%d,%d,%d,%d,%d\n" % (-1, -1, -1, -1, keyValue)
            uart.write(data_str.encode())
            if not debug:
                print(f"{gunId},-1,-1,-1,-1,{keyValue}")
        if debug:
            fps = clock.fps()
            img.draw_string(img.width()-int(65*fontScale), 5, f"{fps:.1f}fps", color=150,scale=fontScale)
        send_image(img)
        if uart.any():
            try:
                cmd = uart.read().decode().strip()
                if cmd:
                    process_command(cmd, 0)
            except:
                pass
        if usb.any():
            try:
                cmd = usb.read().decode().strip()
                if cmd:
                    process_command(cmd, 1)
            except:
                pass
except KeyboardInterrupt:
    print("\nsystem is stopped")
