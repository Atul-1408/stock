import socket
import requests
import sys

# Force IPv4 to fix "getaddrinfo failed" errors on some Windows setups
def force_ipv4_socket_patch():
    print("Applying IPv4 Patch...")
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        # Filter out IPv6 (AF_INET6)
        # Check if family is specified, if so, override to AF_INET if it was AF_UNSPEC
        if 'family' in kwargs:
             if kwargs['family'] == socket.AF_UNSPEC:
                 kwargs['family'] = socket.AF_INET
        elif len(args) > 1 and args[1] == socket.AF_UNSPEC:
             # args is (host, port, family, type, proto, flags)
             lst = list(args)
             lst[1] = socket.AF_INET
             args = tuple(lst)
             
        try:
            # print(f"DEBUG: Resolving {args[0]} with AF_INET")
            responses = old_getaddrinfo(*args, **kwargs)
            # Filter specifically for AF_INET
            return [response for response in responses if response[0] == socket.AF_INET]
        except Exception as e:
            print(f"IPv4 Patch Error for {args}: {e}")
            raise e
            
    socket.getaddrinfo = new_getaddrinfo

force_ipv4_socket_patch()

def test_dns(hostname):
    print(f"Testing DNS for {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"[OK] Success: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"[X] Failed: {hostname} - {e}")
        return False

def test_http(url):
    print(f"Testing HTTP GET for {url}...")
    try:
        response = requests.get(url, timeout=5)
        print(f"[OK] Success: {url} -> Status {response.status_code}")
        return True
    except Exception as e:
        print(f"[X] Failed: {url} - {e}")
        return False

if __name__ == "__main__":
    print(f"Python Executable: {sys.executable}")
    hosts = ["google.com", "query1.finance.yahoo.com", "api.telegram.org"]
    
    print("\n--- DNS TESTS ---")
    for h in hosts:
        test_dns(h)
        
    print("\n--- HTTP TESTS ---")
    test_http("https://query1.finance.yahoo.com/v8/finance/chart/AAPL")
    test_http("https://api.telegram.org")
    
    print("\n--- YFINANCE TEST ---")
    try:
        import yfinance as yf
        t = yf.Ticker("AAPL")
        hist = t.history(period="1d")
        if not hist.empty:
            print(f"[OK] yfinance Success: {len(hist)} rows")
        else:
            print("[X] yfinance Failed: Empty")
    except Exception as e:
        print(f"[X] yfinance Exception: {e}")

    print("\n--- HTTPX ASYNC TEST ---")
    try:
        import httpx
        import asyncio
        async def test_async():
            async with httpx.AsyncClient() as client:
                r = await client.get("https://api.telegram.org")
                print(f"[OK] httpx Success: {r.status_code}")
        
        asyncio.run(test_async())
    except Exception as e:
        print(f"[X] httpx Exception: {e}")


