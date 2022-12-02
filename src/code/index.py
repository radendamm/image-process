# -*- coding: utf-8 -*-

import bottle
import traceback
import oss2
import uuid
import cv2
import os
import json
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color


def oss_get_image_data(context, path):
    parts = path.split('/')
    bucket = parts[0]
    object = '/'.join(parts[1:])
    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(auth, 'oss-' + context.region +
                             '-internal.aliyuncs.com', bucket)
    return oss_client.get_object(object)


def oss_save_image_data(context, img, path):
    parts = path.split('/')
    bucket = parts[0]
    object = '/'.join(parts[1:])
    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(auth, 'oss-' + context.region +
                             '-internal.aliyuncs.com', bucket)
    oss_client.put_object(object, img.make_blob())


def make_response(context, img):
    target = bottle.request.query.get('target')
    if target is not None and len(target) > 0:
        bottle.response.content_type = 'text/plain'
        oss_save_image_data(context, img, target)
        return {'object': target}
    else:
        bottle.response.content_type = 'image/jpeg'
        return img.make_blob()


@bottle.route('/pinjie', method='GET')
def pinjie():
    try:
        image1 = bottle.request.query.get('left')
        image2 = bottle.request.query.get('right')
        print('pinjie images: ', image1, image2)
        context = bottle.request.environ.get('fc.context')
        with Image(file=oss_get_image_data(context, image1)) as f1:
            with Image(file=oss_get_image_data(context, image2)) as f2:
                with Image(width=f1.width + f2.width + 10, height=max(f1.height, f2.height)) as img:
                    img.format = 'jpg'
                    img.composite(f1, left=0, top=0)
                    img.composite(f2, left=f1.width + 10, top=0)
                    return make_response(context, img)
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()


@bottle.route('/watermark', method='GET')
def watermark():
    try:
        image = bottle.request.query.get('img')
        text = bottle.request.query.get('text')
        print('watermark image: {}, text: {}'.format(image, text))
        context = bottle.request.environ.get('fc.context')
        with Drawing() as draw:
            draw.font = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
            draw.fill_color = Color('red')
            draw.font_size = 24
            with Image(width=200, height=50, background=Color('transparent')) as pic:
                draw.text(10, int(pic.height / 2), text)
                draw(pic)
                pic.alpha = True
                pic.format = 'png'
                pic.save(filename='/tmp/water.png')

        with Image(file=oss_get_image_data(context, image)) as img:
            with Image(filename='/tmp/water.png') as water:
                with img.clone() as base:
                    base.format = 'jpg'
                    base.watermark(water, 0.3, 0, int(img.height - 30))
                    return make_response(context, base)
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()


@bottle.route('/format', method='GET')
def format():
    try:
        image = bottle.request.query.get('img')
        fmt = bottle.request.query.get('fmt')
        print('format image: {}, fmt: {}'.format(image, fmt))
        context = bottle.request.environ.get('fc.context')
        with Image(file=oss_get_image_data(context, image)) as img:
            img.format = fmt
            return make_response(context, img)
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()


@bottle.route('/gray', method='GET')
def gray():
    try:
        path = bottle.request.query.get('img')
        parts = path.split('/')
        bucket = parts[0]
        object = '/'.join(parts[1:])
        img_type = object.split('.')[-1]
        context = bottle.request.environ.get('fc.context')
        creds = context.credentials
        auth = oss2.StsAuth(creds.accessKeyId,
                            creds.accessKeySecret, creds.securityToken)
        oss_client = oss2.Bucket(auth, 'oss-' + context.region +
                                 '-internal.aliyuncs.com', bucket)
        fpath = '/tmp/' + str(uuid.uuid4()) + '_' + os.path.split(object)[-1]
        oss_client.get_object_to_file(object, fpath)
        image = cv2.imread(fpath)

        # 转为灰度图像
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        wpath = fpath.replace(".", "_") + '.'+img_type
        cv2.imwrite(wpath, image)
        f = open(wpath, 'rb')
        result = f.read()
        bottle.response.status = '200 OK'
        bottle.response.content_type = 'image/'+img_type
        return result
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()


@bottle.route('/', method='GET')
def index():
    return bottle.template('./index.html')


app = bottle.default_app()

if __name__ == "__main__":
    bottle.run(host='0.0.0.0', port=8080)
