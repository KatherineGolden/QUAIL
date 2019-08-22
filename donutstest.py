# -*- coding: utf-8 -*-
"""
Created on Wed Jul 11 12:47:21 2018

@author: Kate
"""

from donuts import Donuts
from astropy import units as u
import os

def d():
    # Searching in Directory
    imglist = os.listdir('C:/Users/admin/Desktop/NuDomeTracker/CalibrationImages/')
    # Getting Image Names
    images = []
    for i in range(len(imglist)):
        imcheck = imglist[i]
        if imcheck.endswith('.fits'):
            images.append('C:/Users/admin/Desktop/NuDomeTracker/CalibrationImages/' + imcheck)
    # Getting Reference and Science Images
    print("the reference image would be scanned in")
    reference_image_name = images[0]
    science_image_names = []
    for i in range(len(images)):
        science_image_names.append(images[i])

    a = 1 * u.pix
    b = -1 * u.pix
    print(b)

    # Construct a donuts object
    d = Donuts(
            refimage=reference_image_name,
            image_ext=0,
            overscan_width=0,  #was 20
            prescan_width=0,   #was 20
            border=64,
            normalise=True,
            exposure='EXPOSURE',
            subtract_bkg=True,
            ntiles=2)         # was 32
    # for each image, compute the x/y translation required
    # to align the images onto the reference image
    for image in science_image_names:
        shift_result = d.measure_shift(checkimage_filename=image)
        x = shift_result.x
        y = shift_result.y
        if x > a:
            print("the telescope should shift", x, "on the horizontal")
        if x < b:
            print("the telescope should shift", x, "on the horizontal")
        if y > a:
            print("the telescope should shift", y, "on the vertical")
        if y < b:
            print("the telescope should shift", y, "on the vertical")
    fakeresult = [2, 3]
    return fakeresult
      #  print("a new image would now be scanned into science_image_names")






  
