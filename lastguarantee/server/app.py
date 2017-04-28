#coding:utf-8

import os
import sys
import json
import random
import tornado.web
import tornado.httpserver
import tornado.httpclient
import tornado.gen
import tornado.ioloop
from multipart_streamer import MultiPartStreamer, TemporaryFileStreamedPart
from tornado.log import gen_log
from tornado.simple_httpclient import SimpleAsyncHTTPClient


class NoQueueTimeoutHTTPClient(SimpleAsyncHTTPClient):
    """
    Class for implementing None-blocking and No Queue Timeout client with tornado.
    """
    def fetch_impl(self, request, callback):
        key = object()

        self.queue.append((key, request, callback))
        self.waiting[key] = (request, callback, None)

        self._process_queue()

        if self.queue:
            gen_log.debug("max_clients limit reached, request queued. %d active, %d queued requests." % (len(self.active), len(self.queue)))


class MainHandler(tornado.web.RequestHandler):
    """
    Index page Handler class.
    """

    def get(self):

        self.render('index.html')


class MyStreamer(MultiPartStreamer):
    """
    Patch class between tornado streamer decorator and class NoQueueTimeoutHTTPClient
    """

    def create_part(self, headers):

        return TemporaryFileStreamedPart(self, headers=headers)


class DeviceHandler(tornado.web.RequestHandler):
    """
    Class of Device list handler.
    for GET, return device list.
    for POST, modify the existing device list files.
    """

    def get(self):

        with open('device.json') as dev:
            dev_out = json.loads(dev.read())

        with open('update_file.json') as up:
            up_out = json.loads(up.read())

        self.write(json.dumps({
            "filename": up_out["file"],
            "device": dev_out["device"]
        }))

    def post(self):

        ips = self.get_body_argument('start_ip')
        ipe = self.get_body_argument('end_ip')
        if ips.split('.')[:-1] != ipe.split('.')[:-1]:
            self.write(json.dumps({
                "result": "failed",
                "reason": "different ip domin."
            }))
            self.finish()

        domin = '.'.join(ips.split('.')[:-1])
        ips_last = int(ips.split('.')[-1])
        ipe_last = int(ipe.split('.')[-1])

        res = []

        i = ips_last
        while True:
            if i > ipe_last:
                break
            res.append(domin + '.' + str(i))
            i += 1

        with open('device.json', 'w') as dev:
            dev.write(json.dumps(
                {
                    "server": res[0],
                    "device": res
                }
            ))

        self.write(json.dumps({
                "result": "success"
            }))


class UpdateHandler(tornado.web.RequestHandler):
    """
    Main handler of updating. This handler is entirely asynchronous
    """

    connect = set()
    max_connections = 5

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):

        dev = self.get_argument("device")
        try:
            base = self.get_argument("base")
        except tornado.web.MissingArgumentError:
            base = ""

        if self in UpdateHandler.connect:
            # connect already exist
            self.send_error(ip=dev, err='Duplicated connection')
            print UpdateHandler.connect.__len__(), 'Duplicated connection'
        else:
            while True:
                if UpdateHandler.connect.__len__() >= UpdateHandler.max_connections:
                    #print 'Connections arrived limit(max {max}), holding connection {self}, target: {target}'.format(
                        #max=UpdateHandler.max_connections, self=self, target=dev)
                    yield tornado.gen.sleep(random.randint(20, 80)/100)
                else:
                    print 'Connection unfreezed. {self}, target: {target}'.format(self=self, target=dev)
                    UpdateHandler.connect.add(self)
                    break
        with open('update_file.json') as up:
            filename = json.loads(up.read())['file']
        with open('device.json') as svr:
            serv = json.loads(svr.read())['server']

        tornado.httpclient.AsyncHTTPClient.configure(NoQueueTimeoutHTTPClient)
        http_client = tornado.httpclient.AsyncHTTPClient()

        try:
            response = yield http_client.fetch(
                "http://{device}:5556/?file={filename}&server={server}&base_dir={base}".format(
                    device=dev, filename=filename, server=serv, base=base),
                connect_timeout=10.0,
                request_timeout=120.0
            )
            http_client.close()
            UpdateHandler.connect.remove(self)
            self.write(json.dumps({
                "result": "success",
                "ip": dev
            }))

        except:
            self.write(json.dumps({
                "result": "failed",
                "ip": dev
            }))


@tornado.web.stream_request_body
class FileUploader(tornado.web.RequestHandler):
    """
    Handler for upload files. Patched with MyStreamer class, so it can overreach the limit of
    tornado max-body-size(default 100M).
    """

    def prepare(self):
        if self.request.method.lower() == 'post':
            self.request.connection.set_max_body_size(1024*1024*1024*1024)

        try:
            total = int(self.request.headers.get("Content-Length", "0"))
        except KeyError:
            total = 0

        self.ps = MyStreamer(total=total)

    def data_received(self, chunk):
        self.ps.data_received(chunk)

    def post(self):
        try:
            self.ps.data_complete()
        finally:
            fn = self.get_argument('filename')
            self.ps.part.move(os.path.join(os.path.dirname(__file__), 'files/' + fn))
            self.ps.release_parts()
            with open('update_file.json', 'w') as up:
                up.write(json.dumps({"file": fn}))
            self.redirect('/')

app = tornado.web.Application(
    handlers=[
        (r'/', MainHandler),
        (r'/file', FileUploader),
        (r'/device_list', DeviceHandler),
        (r'/request', UpdateHandler)
    ],
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    debug=True
)

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(
        app,
        max_body_size=1024*1024,
        max_buffer_size=1024*1024
    )
    http_server.listen(5555)
    tornado.ioloop.IOLoop.instance().start()
