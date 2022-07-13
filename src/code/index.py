# -*- coding: utf-8 -*-

import bottle
import traceback
import oss2
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

@bottle.route('/pinjie', method='GET')
def pinjie():
    try:
        bottle.response.content_type = 'image/jpeg'
        image1 = bottle.request.query.get('left')
        image2 = bottle.request.query.get('right')
        print('pinjie images: ', image1, image2)
        context = bottle.request.environ.get('fc.context')
        with Image(file=oss_get_image_data(context, image1)) as f1:
            with Image(file=oss_get_image_data(context, image2)) as f2:
                with Image(width=f1.width+f2.width+10, height=max(f1.height, f2.height)) as img:
                    img.format = 'jpg'
                    img.composite(f1, left=0, top=0)
                    img.composite(f2, left=f1.width+10, top=0)
                    return img.make_blob()
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()

@bottle.route('/watermark', method='GET')
def watermark():
    try:
        bottle.response.content_type = 'image/jpeg'
        image = bottle.request.query.get('img')
        text = bottle.request.query.get('text')
        print('watermark image: {}, text: {}'.format(image, text))
        context = bottle.request.environ.get('fc.context')
        with Drawing() as draw:
            draw.font = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
            draw.fill_color = Color('red')
            draw.font_size = 24
            with Image(width=200, height=50, background=Color('transparent')) as pic:
                draw.text(10, int(pic.height/2), text)
                draw(pic)
                pic.alpha = True
                pic.format = 'png'
                pic.save(filename='/tmp/water.png')

        with Image(file=oss_get_image_data(context, image)) as img:
            with Image(filename='/tmp/water.png') as water:
                with img.clone() as base:
                    base.format = 'jpg'
                    base.watermark(water, 0.3, 0, int(img.height-30))
                    return base.make_blob()
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()


@bottle.route('/format', method='GET')
def format():
    try:
        bottle.response.content_type = 'image/jpeg'
        image = bottle.request.query.get('img')
        fmt = bottle.request.query.get('fmt')
        print('format image: {}, fmt: {}'.format(image, fmt))
        context = bottle.request.environ.get('fc.context')
        with Image(file=oss_get_image_data(context, image)) as img:
            img.format = fmt
            return img.make_blob()
    except Exception as ex:
        bottle.response.content_type = 'text/plain'
        return 'ERROR: ' + traceback.format_exc()

@ bottle.route('/', method='GET')
def index():
    return bottle.template('./index.html')

app = bottle.default_app()

if __name__ == "__main__":
    bottle.run(host='0.0.0.0', port=8080)
