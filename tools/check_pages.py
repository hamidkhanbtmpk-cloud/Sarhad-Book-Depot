import urllib.request, time
paths=['/','/login','/admin/attendance','/admin/salary/slip/1']
# wait a moment for server to start
time.sleep(2)
for p in paths:
    url='http://127.0.0.1:5000'+p
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            print(p, r.status)
            data = r.read(2000).decode('utf-8',errors='replace')
            print(data[:800])
            print('---')
    except Exception as e:
        print(p, 'ERROR', str(e))
