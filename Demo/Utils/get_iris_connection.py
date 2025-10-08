import iris

def get_cursor():
    ## Credentials: 
    server_location = "localhost"
    port_number = 32782
    namespace = "DEMO"
    user_name = "_SYSTEM"
    password = "ISCDEMO"

    ## Create a connection
    conn = iris.connect(server_location, port_number, namespace, user_name, password)

    ## Create a cursor object
    cursor = conn.cursor()
    return cursor
    