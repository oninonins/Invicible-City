import urllib.request, os, sys

url = sys.argv[1]
out = sys.argv[2]
print(f"Downloading {url} -> {out}")
urllib.request.urlretrieve(url, out)
size = os.path.getsize(out)
print(f"Done: {size} bytes ({size/1024/1024:.1f} MB)")
