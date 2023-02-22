def returnTrue(num):
    try:
        return True
    except:
        return False


def test_test():
    assert returnTrue(6) == True
