# automatically generated by the FlatBuffers compiler, do not modify

# namespace: State

import flatbuffers

class FlatBufferPosRot(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsFlatBufferPosRot(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = FlatBufferPosRot()
        x.Init(buf, n + offset)
        return x

    # FlatBufferPosRot
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # FlatBufferPosRot
    def Position(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            x = o + self._tab.Pos
            from .FlatBufferVec3 import FlatBufferVec3
            obj = FlatBufferVec3()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # FlatBufferPosRot
    def Rotation(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            x = o + self._tab.Pos
            from .FlatBufferQuat import FlatBufferQuat
            obj = FlatBufferQuat()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

def FlatBufferPosRotStart(builder): builder.StartObject(2)
def FlatBufferPosRotAddPosition(builder, position): builder.PrependStructSlot(0, flatbuffers.number_types.UOffsetTFlags.py_type(position), 0)
def FlatBufferPosRotAddRotation(builder, rotation): builder.PrependStructSlot(1, flatbuffers.number_types.UOffsetTFlags.py_type(rotation), 0)
def FlatBufferPosRotEnd(builder): return builder.EndObject()
