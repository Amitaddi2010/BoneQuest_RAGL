import pkg_resources
try:
    dist = pkg_resources.get_distribution('pageindex')
    print("Found package:", dist.project_name)
    print("Location:", dist.location)
    try:
        top_lvl = dist.get_metadata('top_level.txt')
        print("Top level modules:", top_lvl)
    except:
        print("No top_level.txt")
except Exception as e:
    print("Error:", e)
