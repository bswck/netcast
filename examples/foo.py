import netcast as nc


class Foo(nc.Model):
    baz = nc.Int64(default=-5)
    biz = nc.Int64(version_added=1, default=3)

