import urllib.request, urllib.parse, http.cookiejar, time
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_url = 'http://127.0.0.1:5000/login'
attendance_url = 'http://127.0.0.1:5000/admin/attendance'
salary_url = 'http://127.0.0.1:5000/admin/salary/slip/1'

# perform login
login_data = urllib.parse.urlencode({'username':'admin','password':'admin123'}).encode()
try:
    r = opener.open(login_url, data=login_data, timeout=8)
    print('Login response URL:', r.geturl(), 'Status:', r.getcode())
except Exception as e:
    print('Login ERROR', e)
    raise SystemExit(1)

# fetch protected pages
for url in (attendance_url, salary_url):
    try:
        r = opener.open(url, timeout=8)
        print('\nFetched', url, 'Status', r.getcode())
        data = r.read(1500).decode('utf-8', errors='replace')
        print(data[:1000])
    except Exception as e:
        print('Fetch ERROR', url, e)
