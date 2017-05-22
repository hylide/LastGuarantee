# -*- coding:utf-8 -*-

import os
import time

res = os.popen("ps -aux | grep VAS | grep -v 'grep' | awk '{print $8}'").read()
print res
if 'Z' in res or 'D' in res:
    time.sleep(5)
    res = os.popen("ps -aux | grep VAS | grep -v 'grep' | awk '{print $8}'").read()
    if 'Z' in res or 'D' in res:
        with open('/usr/local/VionSoftware/LastGuarantee/client/cron.log', 'a+') as f:
            f.write(time.ctime() + '  catch status exception: ' + res.replace('\n', '\t'))
            f.write('system will reboot soon.')
        os.system('reboot')
