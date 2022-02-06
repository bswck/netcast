import asyncio
from typing import ClassVar, Type

import pytest

from netcast import ArrangementConstructionError
from netcast.tools.arrangements import CT_DEFAULT, AT
from netcast.tools.arrangements import ClassArrangement
from netcast.tools.contexts import CT
from netcast.tools.collections import Params, ForwardDependency


class _TestContextType:
    context: CT
    context_class: ClassVar[Type[CT]]

    def test(self, cls: AT):
        if cls.context_class is None:
            expected_context_class = CT_DEFAULT
        else:
            expected_context_class = cls.context_class
        assert type(self.context) is expected_context_class is self.context_class


class TestClassArrangement:
    def test_config(self):
        from netcast.tools.contexts import ListContext

        class F(ClassArrangement, config=True):
            context_class = ListContext

            def test(self):
                assert self.context is None

        class CA1(ClassArrangement, descent=F):
            context_class = None

            def test(self):
                assert self.context_class is F.context_class
                assert isinstance(self.context, F.context_class)

        class CA2(F):
            def test(self):
                assert isinstance(self.context, F.context_class)

        from netcast.tools.contexts import QueueContext as SomeOtherContext

        with pytest.raises(ArrangementConstructionError):

            class E(ClassArrangement, descent=F):
                context_class = SomeOtherContext

        CA1().test()
        CA2().test()

    def test_context_type(self, injected_class_arrangement):
        class CA1(injected_class_arrangement, _TestContextType):
            pass

        class CA2(injected_class_arrangement, _TestContextType, descent=CA1):
            new_context = True

        CA1().test(injected_class_arrangement)
        CA2().test(injected_class_arrangement)

    def test_descent(self, injected_class_arrangement):
        class CA1(injected_class_arrangement):
            pass

        class CA2(CA1):
            def test(self):
                assert self.descent_type is CA1
                assert self.context is CA1.context

        class CA3(CA1, descent=CA2):  # this one's interesting.
            def test(self):
                assert self.descent_type is CA2
                assert self.context is CA1.context

        class CA4(injected_class_arrangement, descent=CA1):
            def test(self):
                assert self.descent_type is CA1
                assert self.context is CA2.context

        CA2().test()
        CA3().test()
        CA4().test()

    def test_new_context(self, injected_class_arrangement):
        class CA1(injected_class_arrangement):
            def test(self):
                assert self.supercontext is None

        class CA2(injected_class_arrangement, descent=CA1):
            new_context = True

            def test(self):
                assert self.supercontext is CA1.context
                assert self.context is CA2.context

        class CA3(injected_class_arrangement, descent=CA1):
            new_context = None  # default one

            def test(self):
                assert self.context is CA1.context

        class CA4(injected_class_arrangement, descent=CA3):
            new_context = True

            def test(self):
                assert self.supercontext is CA3.context is CA1.context
                assert self.context is CA4.context

        class CA5(injected_class_arrangement, descent=CA4):
            def test(self):
                CA4.test(self)  # type: ignore

        class CA6(injected_class_arrangement, descent=CA5):
            new_context = True

            def test(self):
                assert self.supercontext is CA5.context
                assert self.context is CA6.context

        CA1().test()
        CA2().test()
        CA3().test()
        CA4().test()
        CA5().test()
        CA6().test()

    def test_class_dict_arrangement(self):
        from netcast.tools.arrangements import ClassDictArrangement

        class CA1(ClassDictArrangement):
            context_params = Params.frame(pings=0, pongs=0)

            def ping(self):
                self.context.pings += 1

        class CA2(CA1):
            def pong(self):
                self.context.pongs += 1

        ca1 = CA1()
        ca1.ping()
        ca2 = CA2()
        ca2.pong()

        assert CA1.context is CA2.context
        assert ca1.context is ca2.context
        assert ca1.context == {"pings": 1, "pongs": 1}

        ca1.ping()
        ca2.pong()

        assert ca1.context == {"pings": 2, "pongs": 2}

        ca2.ping()

        assert ca1.context == {"pings": 3, "pongs": 2}

    def test_class_list_arrangement(self):
        from netcast.tools.arrangements import ClassListArrangement

        class CA(ClassListArrangement, _TestContextType):
            pass

        CA().test(ClassListArrangement)

        class CA1(ClassListArrangement):
            def one(self):
                self.context.append(1)

        class CA2(CA1):
            def two(self):
                self.context.append(2)

        ca1 = CA1()
        ca1.one()
        ca2 = CA2()
        ca2.two()

        assert ca2.context == [1, 2]

        ca2.one()

        assert ca2.context.pop() == 1
        assert ca2.context == [1, 2]

    def test_class_queue_arrangement(self):
        from netcast.tools.arrangements import ClassQueueArrangement

        class CQA(ClassQueueArrangement):
            get = ForwardDependency()
            put = ForwardDependency()

        class Get(ClassQueueArrangement, descent=CQA):
            def __call__(self):
                return self.context.get()

        CQA.get.dependency(Get)

        class Put(ClassQueueArrangement, descent=CQA):
            def __init__(self, *args):
                """We do this to check if ForwardDependency() guessed the unbound param well"""
                assert not args

            def __call__(self, item):
                self.context.put(item)

        CQA.put.dependency(Put)

        qa = CQA()
        assert qa.context is qa.put.context
        assert qa.context is qa.get.context

        qa.put(1)
        assert qa.context.qsize() == 1

        qa.get()
        assert qa.context.qsize() == 0

    @pytest.mark.asyncio
    async def test_class_asyncio_queue_arrangement(self):
        from netcast.tools.arrangements import ClassAsyncioQueueArrangement

        class QP(ClassAsyncioQueueArrangement):
            async def __call__(self, item):
                await self.context.put(item)

        class QG(ClassAsyncioQueueArrangement, descent=QP):
            async def __call__(self):
                return await self.context.get()

        put = QP()
        get = QG()
        queue = put.context

        await asyncio.gather(put(1), put(5), get(), put(3))
        assert queue.qsize() == 2
        await asyncio.gather(get(), put(2), get(), get())
        assert queue.qsize() == 0


class TestArrangement:
    def test_context_type(self, injected_arrangement):
        class A1(injected_arrangement, _TestContextType):
            pass

        class A2(injected_arrangement, _TestContextType, descent=A1):
            new_context = True

        a1 = A1()
        a1.test(injected_arrangement)
        A2(a1).test(injected_arrangement)  # noqa

    def test_new_context(self, injected_arrangement):
        class A1(injected_arrangement):
            def test(self):
                assert self.supercontext is None
                assert not self.has_new_context

        class A2(injected_arrangement, descent=A1):
            def test(self):
                assert self.context is self.descent.context
                assert not self.has_new_context

        class A3(injected_arrangement, descent=A2):
            new_context = True

            def test(self):
                assert self.supercontext is a1.context
                assert self.supercontext is self.descent.context
                assert self.context is not a1.context
                assert self.context is not self.descent.context
                assert self.has_new_context

        class A4(injected_arrangement, descent=A3):
            def test(self):
                assert self.supercontext is self.descent.supercontext
                assert self.context is self.descent.context
                assert not self.has_new_context

        a1 = A1()
        a2 = A2(a1)
        a3 = A3(a2)
        a4 = A4(a3)
        a1.test()
        a2.test()
        a3.test()
        a4.test()

        assert a1.subcontexts == (a3.context,)

    def test_dict_arrangement(self):
        from netcast.tools.arrangements import DictArrangement

        class DA1(DictArrangement):
            context_params = Params.frame(pings=0, pongs=0)

            def clear(self):
                self.context.update(**self.context_params.kwargs)

            def ping(self):
                self.context.pings += 1

            def pong(self):
                self.context.pongs += 1

        class DA2(DA1):
            pass

        da1 = DA1()
        da2 = DA2(da1)
        assert da1.context.pings == 0
        assert da2.context.pings == 0
        assert da1.context.pongs == 0
        assert da2.context.pongs == 0

        da2.ping()
        assert da1.context.pings == 1
        assert da1.context.pongs == 0
        assert da2.context.pings == 1
        assert da2.context.pongs == 0

        da1.pong()
        assert da1.context.pings == 1
        assert da1.context.pongs == 1
        assert da2.context.pings == 1
        assert da2.context.pongs == 1

        da1.clear()
        assert da1.context.pings == 0
        assert da2.context.pings == 0
        assert da1.context.pongs == 0
        assert da2.context.pongs == 0

    def test_list_arrangement(self):
        from netcast.tools.arrangements import ListArrangement

        class LA(ListArrangement):
            def __call__(self, x):
                self.context.append(x)

        class LP(ListArrangement, descent=LA):
            def __call__(self, x=-1):
                return self.context.pop(x)

        class LE(ListArrangement, descent=LA):
            def __call__(self, x):
                self.context.extend(x)

        append = LA()
        pop = LP(append)
        with pytest.raises(TypeError):
            LE(pop)

        extend = LE(append)
        unbound = LE()
        assert unbound.context is not extend.context

        context = append.context
        append(5)
        assert context == [5]
        assert pop() == 5
        assert not context

        extend([1, 2, 3])
        assert context == [1, 2, 3]

        context.clear()
        assert not context

        foreign_appender = LA()
        assert foreign_appender.context is not context

    def test_string_io_arrangement(self):
        from netcast.tools.arrangements import StringIOArrangement

        class SA(StringIOArrangement):
            read = ForwardDependency()
            write = ForwardDependency()

            def seek(self, offset, whence=0):
                return self.context.seek(offset, whence)

            def tell(self):
                return self.context.tell()

        @SA.read.dependency
        class AR(StringIOArrangement, descent=SA):
            def __call__(self, nchars=-1):
                return self.context.read(nchars)

        @SA.write.dependency
        class AW(StringIOArrangement, descent=SA):
            def __call__(self, chars):
                self.context.write(chars)

        sa = SA()

        assert isinstance(sa.read, AR)
        assert isinstance(sa.write, AW)
        assert sa.context is sa.read.context
        assert sa.read.context is sa.write.context
        assert sa.read() == ""

        sa.write("hello")
        sa.seek(0)
        content = sa.read()
        assert content == "hello"

        sa_offset = sa.seek(1)
        assert sa.read() == content[sa_offset:]

    def test_queue_arrangement(self):
        from netcast.tools.arrangements import QueueArrangement

        class QA(QueueArrangement):
            put = ForwardDependency()
            get = ForwardDependency()

        class QP(QueueArrangement, descent=QA):
            def __call__(self, item):
                self.context.put(item)

        QA.put.dependency(QP)

        class QG(QueueArrangement, descent=QA):
            def __call__(self):
                return self.context.get()

        QA.get.dependency(QG)

        qa = QA()
        assert qa.context is qa.put.context
        assert qa.context is qa.get.context

        qa.put(1)
        assert qa.context.qsize() == 1

        qa.get()
        assert qa.context.qsize() == 0

    def test_construct_arrangement(self):
        from netcast.tools.contexts import ConstructContext
        from netcast.tools.arrangements import wrap_to_arrangement

        ConstructArrangement = wrap_to_arrangement(
            "ConstructArrangement", ConstructContext
        )

        class CSA1(ConstructArrangement):
            pass

        class CSA2(CSA1):
            new_context = True

        csa1 = CSA1()
        csa2 = CSA2(csa1)  # type: ignore

        # Initially, we test if all that's primary works OK
        assert csa1.context is not csa2.context
        assert csa2.supercontext is csa1.context

        # Now, test the underlying conditions
        assert csa2.context == {"_": csa2.supercontext}
        assert csa2.context._ == {}

        test_val = 1
        csa2.context._.test_item = test_val
        csa2.context.test_item = test_val

        assert csa2.context.test_item is test_val
        assert csa2.context._.test_item is test_val
        assert csa2.supercontext.test_item is csa2.context.test_item  # type: ignore

    @pytest.mark.asyncio
    async def test_asyncio_queue_arrangement(self):
        from netcast.tools.arrangements import AsyncioQueueArrangement

        class QP(AsyncioQueueArrangement):
            async def __call__(self, item):
                await self.context.put(item)

        class QG(AsyncioQueueArrangement, descent=QP):
            async def __call__(self):
                return await self.context.get()

        put = QP()
        get = QG(put)
        queue = put.context

        await asyncio.gather(put(1), put(5), get(), put(3))
        assert queue.qsize() == 2
        await asyncio.gather(get(), put(2), get(), get())
        assert queue.qsize() == 0
