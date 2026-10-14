$TTL 3D
@       IN      SOA   ns.example.com. admin.example.com. (
                2024100901
                8H
                2H
                4W
                1D)

@       IN      NS    10.9.0.153
@       IN      A     1.2.3.4
www     IN      A     4.3.2.1
ns      IN      A     10.9.0.153
*       IN      A     1.2.3.6
