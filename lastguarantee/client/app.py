# -*-:coding -*-

import httplib
import web
import os
import json

base = '/usr/local/VionSoftware/'


class IndexHandler:

    def GET(self):
        try:
            request = web.input()
            print request.get('file')
            print request.get('base_dir')
            base_dir= request.get('base_dir') | base
            filename = request.get('file')
            server = request.get('server')
        except KeyError:
            return json.dumps({
                "result": "failed"
            })

        headers = {
            "Content-type": "multipart/form-data",
            "Pragma": "no-cache",
            "Cache-Control": "must-revalidate"
        }
        os.chdir('{base}LastGuarantee/client/'.format(base=base_dir))
        conn = httplib.HTTPConnection('{server}'.format(server=server), port=5557)
        conn.request("GET", '/' + filename, headers=headers)
        conn.close()
        httpres = conn.getresponse()
        with open(filename, 'wb') as fn:
            fn.write(httpres.read())
        os.system('rm -rf {base}*.gz'.format(base=base_dir))
        os.system('cp {filename} {base}'.format(filename=filename, base=base_dir))
        pname = filename.split('_')[0]
        os.system('mv {base}'.format(base=base_dir) + pname + ' ' + base_dir + pname + '_bak')
        os.chdir(base_dir)
        os.system('tar zxvf {filename}'.format(filename=filename))
        os.system('rm -rf {base}*bak*'.format(base=base_dir))
        os.system('pkill -9 ' + pname)
        os.system('rm *.gz')

        return json.dumps({
                "result": "success"
            })


class UpdateHandler:

    def GET(self):
        request = web.input()


if __name__ == '__main__':
    urls = [
        ('/', 'IndexHandler'),
        ('/update', 'UpdateHandler')
    ]

    app = web.application(urls, globals())
    app.run()

