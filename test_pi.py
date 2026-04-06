import os
import sys

try:
    import pageindex
    print("pageindex is imported!")
    print(dir(pageindex))
    from pageindex import PageIndexClient
    client = PageIndexClient(api_key="63e1e606e28a4d11a6e083cf8e160a93")
    print(dir(client))
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()

