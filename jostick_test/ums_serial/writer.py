#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created Date: May 15. 2020
Copyright: UNMAND SOLUTION
Author: Dae Jong Jin 
Description: Pyserial Write
'''

import serial
import time
import threading


class UMDSerialWriter():
    def __init__(self, serial):
        self.__serial = serial

    def run(self, send_data):
        # print(self.__send_data)
        try:
            result = send_data
            self.__serial.write(result.encode('utf-8'))
            print(result.encode('utf-8'))
        except:
            print("시리얼 연결이 끊어졌습니다.")
            self.reopen()

    def reopen(self):
        try:
            self.__serial = serial.Serial(
                port='/dev/opencm',
                baudrate=9600
            )
            print("시리얼이 재 연결되었습니다.")

        except:
            print(u' 포트를 다시 연결해 주세요')
        time.sleep(1)


