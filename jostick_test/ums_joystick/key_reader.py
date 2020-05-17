#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, struct, array, time
import threading
from fcntl import ioctl

from .key_names import axis_names, button_names
from jostick_test.ums_serial.writer import UMDSerialWriter

class JoystickReader():

    axis_states = {}
    button_states = {}  
    tmp_axis_map = []
    axis_map = []
    button_map = []

    def __init__(self,serial):
        self.__serial = serial
        self.__num_buttons = None
        self.__num_axes = None
        self.__jsdev = None
        self.__fn = '/dev/realsense'
        self.__dir = '/dev/input'
        self.__writer = UMDSerialWriter(serial=self.__serial)
        # self.__ums_serial = UMDSerial()

    def joy_check(self):

        try:
            print('Opening %s...' % self.__fn)
            self.__jsdev = open(self.__fn, 'rb')

            if self.__jsdev:
                print("조이스틱 체크 성공")
                return True
        except:
            print("조이스틱 체크 실패")
            return False

    def joy_open(self):
        print("조이스틱의 접속을 확인하는 중입니다.")
        while True:
            is_open = self.joy_check()
            if is_open == True:
                print("조이스틱을 불러옵니다.")
                break
            time.sleep(1.0)
        # print("Opening ")
            # print('Opening %s...' % dir)
            # self.__jsdev = open(dir, 'rb')


    def joy_read(self):
        buf = array.array('B', [0] * 0x05)
        buf[0] = 0x00
        buf[1] = 0x01
        buf[2] = 0x02
        num_buf = 3

        for axis in buf[:num_buf]:
            axis_name = axis_names.get(axis, 'unknown')
            print("axis : {0}, axis_name: {1}".format(hex(axis), axis_name))
            self.axis_map.append(axis_name)
            self.tmp_axis_map.append(hex(axis))
            self.axis_states[hex(axis)] = 0.0

        print("axis_map : {0}".format(', '.join(self.axis_map)))
        print("tmp_axis_map : {0}".format(', '.join(self.tmp_axis_map)))
        print("axis_states : {0}".format(self.axis_states))

    def joy_name_read(self):
        buf = array.array('B', [0] * 64)
        # 드라이버로부터 조이스틱 이름 가져오기
        ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
        js_name = buf.tobytes().rstrip(b'\x00').decode('utf-8') # 0x00 비어있는 값 제거 
        print('Device name: %s' % js_name)

    def axis_read(self):
        # 드라이버로부터 축 개수 가져오기
        buf = array.array('B', [0])
        ioctl(jsdev, 0x80016a11, buf) # JSIOCGAXES
        # x,y 축이면 2
        num_axes = buf[0]

        # Get the axis map.
        # 키 맵핑
        buf = array.array('B', [0] * 0x40)
        ioctl(jsdev, 0x80406a32, buf) # JSIOCGAXMAP
        # 읽은 값에서 총 축 수만큼 loop 돌림
        for axis in buf[:num_axes]:
            # axis_names의 첫번째 번호와 같은 이름을 가져온다.
            # 예를들어 axis가 0이면 axis_names에서 0x00 > 'x'를 가져오고
            # axis가 1이면 axis_names에 0x01 > 'y'를 가져오기 된다.
            axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            # 해당 축 0.0 으로 초기화 
            self.axis_states[self.axis_name] = 0.0

    def button_read(self):
        # 드라이버로부터 버튼 개수 가져오기
        buf = array.array('B', [0])
        ioctl(jsdev, 0x80016a12, buf) # JSIOCGBUTTONS
        # 버튼이 두 개면 2
        num_buttons = buf[0]

        # Get the button map.
        # 축과 마찬가지로 버튼 번호로 이름을 가져온다.
        buf = array.array('H', [0] * 200)
        ioctl(jsdev, 0x80406a34, buf) # JSIOCGBTNMAP

        for btn in buf[:num_buttons]:
            btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[self.btn_name] = 0

    def joy_main_event(self):
        # Main event loop
        # 키 이벤트 처리
        while True:
            # 키 읽기 블록 상태(Block) 
            # 키 입력이 들어오기 전까지 무조건 대기
            try:
                evbuf = jsdev.read(8)
                # 이벤트가 발생했다면
                if evbuf:
                    # 시간, 값, 타입, 번호 등으로 가져옴
                    time, value, type, number = struct.unpack('IhBB', evbuf)

                    # type이 0x80이면 장치 초기 상태이다.
                    if type & 0x80:
                        print("(initial)", end="")

                    # type이 0x01 버튼이 눌렸거나 떨어졌을때이다.
                    if type & 0x01:
                        # number 값으로 해당 버튼 이름 가져오기
                        button = self.button_map[number]
                        if button:
                            # 해당 버튼 상태(button_states)에 value 값으로 변경          
                            self.button_states[button] = value
                            if value:
                                print("%s pressed" % (button))
                            else:
                                print("%s released" % (button))


                            send_button_data = str(number)
                            send_button_value_data = str(value)
                            send_data = send_button_data + send_button_value_data
                            self.__writer.run(send_data)

                            print("{0} - {1} : \t{2}".format(send_button_data, button, send_button_value_data))

                    # type이 0x02이면 축이 이동한 상태이다.
                    if type & 0x02:
                        # number로 해당 축의 이름 가져오기
                        axis = self.axis_map[number]
                        if axis:
                            # 값을 32767로 나눠서 0 또는 1, -1 로 표시
                            # 축 값이 -32767 ~ 0 ~ 32767 사이 값으로 표시되는 데
                            # 0보다 큰지 작은지 0인지를 구분하기 위함이다.
                            fvalue = value / 32767.0
                            # 상태값(0, 1, -1)을 저장
                            self.axis_states[axis] = fvalue
                            print("%s: %.3f" % (axis, fvalue))

                            send_axis_data = str(number)
                            send_axis_value_data = str(axis_states[axis])
                            send_data = send_axis_data + send_axis_value_data
                            self.__writer.run(send_data)

                            print("{0} - {1} : \t{2}".format(send_axis_data, axis, send_axis_value_data))
            except:
                self.reconect()
            
    def reconect():
        try:
            print("조이스틱을 재 연결합니다.")
            print('Opening %s...' % self.__fn)
            self.__jsdev = open(self.__fn, 'rb')

            if self.__jsdev:
                print("조이스틱 체크 성공")
                return True
        
        except:
            print("조이스틱을 다시 연결하세요..")
        time.sleep(1)

    def joy_test(self):
        try :
            while True :
                
                try:
                    print(" --- Test ---")
                    # test_input = int(input(" 입력하세요 : "))
                    test_input = 0x01
                    self.__writer.run(hex(test_input))

                    self.__jsdev = open(self.__fn, 'rb')
                    if self.__jsdev:
                        print("조이스틱 체크 성공")
                    time.sleep(1)
                        # return True

                    # if test_input in self.tmp_axis_map :
                    #     pass
                    #     # print(tmp_axis_map[1])
                        
                    # else :
                    #     print(" 존재하지 않습니다..")
                except ValueError :
                    print("잘못된 입력입니다.")
                except FileNotFoundError :
                    print("조이스틱 연결이 끊어졌습니다.")
                    try:
                        self.__jsdev = open(self.__fn, 'rb')
                        print("조이스틱 재 연결되었습니다.")
                    except:
                        print("조이스틱을 다시 연결해 주세요")
                    time.sleep(1)

        except KeyboardInterrupt as e:
            print(" ctrl + c pressed !!")
            print("exit .. ")


    # threading
    # def write(self, data):
    #     self.__writer = UMDSerialWriter(serial=self.__serial, send_data = hex(data))
    #     t = threading.Thread(target = self.__writer.run, args="")
    #     t.start()
