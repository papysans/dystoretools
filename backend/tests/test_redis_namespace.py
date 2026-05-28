from dystore.cache.redis import NS_COOKIES, NS_RATELIMIT, NS_TASKS, NS_WS, key


def test_namespaces_distinct() -> None:
    assert len({NS_COOKIES, NS_TASKS, NS_RATELIMIT, NS_WS}) == 4


def test_key_join() -> None:
    assert key(NS_COOKIES, "doudian", "session") == "cookies:doudian:session"
    assert key(NS_TASKS, "queue") == "tasks:queue"
