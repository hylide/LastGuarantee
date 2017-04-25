#coding:utf-8

import os
import sys
import json
import tornado.web
import tornado.httpserver
import tornado.httpclient
import tornado.gen
import tornado.ioloop
from multipart_streamer import MultiPartStreamer, TemporaryFileStreamedPart
from tornado.log import gen_log
from tornado.simple_httpclient import SimpleAsyncHTTPClient

base_dir = os.path.dirname(__file__)

class NoQueueTimeoutHTTPClient(SimpleAsyncHTTPClient):
    def fetch_impl(self, request, callback):
        key = object()

        self.queue.append((key, request, callback))
        self.waiting[key] = (request, callback, None)

        self._process_queue()

        if self.queue:
            gen_log.debug("max_clients limit reached, request queued. %d active, %d queued requests." % (len(self.active), len(self.queue)))


class MainHandler(tornado.web.RequestHandler):

    def get(self):

        self.render('index.html')


class MyStreamer(MultiPartStreamer):

    def create_part(self, headers):

        return TemporaryFileStreamedPart(self, headers=headers)


class DeviceHandler(tornado.web.RequestHandler):

    def get(self):

        with open(base_dir + '/device.json') as dev:
            dev_out = json.loads(dev.read())

        with open(base_dir + '/update_file.json') as up:
            up_out = json.loads(up.read())

        self.write(json.dumps({
            "filename": up_out["file"],
            "device": dev_out["device"]
        }))


class UpdateHandler(tornado.web.RequestHandler):

    connect = set()
    max_connections = 3

    def write_error(self, status_code, **kwargs):
        self.finish(json.dumps({
            "result": "failed",
            "ip": kwargs["ip"],
            "err": kwargs["err"]
        }))

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
                    print 'Connections arrived limit(max 3), holding connection now'
                    yield tornado.gen.sleep(0.5)
                else:
                    print 'Connection unfreezed.'
                    UpdateHandler.connect.add(self)
                    break
        with open(base_dir + '/update_file.json') as up:
            filename = json.loads(up.read())['file']
        with open(base_dir + '/device.json') as svr:
            serv = json.loads(svr.read())['server']

        tornado.httpclient.AsyncHTTPClient.configure(NoQueueTimeoutHTTPClient)
        http_client = tornado.httpclient.AsyncHTTPClient()
        try:
            response = yield http_client.fetch(
                "http://{device}:5556/?file={filename}&server={server}&base_dir={base}".format(
                    device=dev, filename=filename, server=serv, base=base))
            http_client.close()
            UpdateHandler.connect.remove(self)
            self.write(json.dumps({
                "result": "success",
                "ip": dev
            }))

            self.finish()
        except:
            http_client.close()
            UpdateHandler.connect.remove(self)
            self.send_error(ip=dev, err=str(sys.exc_info()[0]))


@tornado.web.stream_request_body
class FileUploader(tornado.web.RequestHandler):

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
