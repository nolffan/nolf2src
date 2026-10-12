#!/usr/bin/env python3
"""Read initialised data out of a shipped image by virtual address.

The error-reporting macros are the reason this exists. Half the check sites
push a string literal, which a disassembly already shows; the other half push
a `static char*` holding the name, and there the disassembly only shows the
address of the pointer. One dereference recovers the name, which is the
difference between guessing a tag and knowing it.

  tools/dataref.py out/reference/lithtech.exe 0x4a8088 0x4a7110
      0x004a8088  -> 0x004a8090  "ILTClient::GetSurfaceAlpha"
      0x004a7110  -> 0x004a7114  "LT ERROR: %s returned %s (%s)"

Each address is reported three ways where they apply: the string that starts
there, the dword stored there, and - if that dword is itself an address in the
image - the string it points at.
"""
import struct
import sys


class Image:
	def __init__(self, path):
		self.d = open(path, 'rb').read()
		pe = struct.unpack_from('<I', self.d, 0x3c)[0]
		nsec = struct.unpack_from('<H', self.d, pe + 6)[0]
		optsize = struct.unpack_from('<H', self.d, pe + 20)[0]
		self.base = struct.unpack_from('<I', self.d, pe + 24 + 28)[0]
		self.secs = []
		for i in range(nsec):
			o = pe + 24 + optsize + i * 40
			name = self.d[o:o + 8].rstrip(b'\0').decode('latin1')
			vsize, va, rawsize, raw = struct.unpack_from('<IIII', self.d, o + 8)
			self.secs.append((name, self.base + va, min(vsize, rawsize) or rawsize, raw))

	def offset(self, va):
		for name, start, size, raw in self.secs:
			if start <= va < start + size:
				return raw + (va - start)
		return None

	def dword(self, va):
		o = self.offset(va)
		return struct.unpack_from('<I', self.d, o)[0] if o is not None else None

	def string(self, va, limit=200):
		o = self.offset(va)
		if o is None:
			return None
		end = self.d.find(b'\0', o, o + limit)
		if end < 0:
			return None
		s = self.d[o:end]
		if not all(32 <= c < 127 or c in (9, 10, 13) for c in s):
			return None
		return s.decode('latin1')


def main():
	if len(sys.argv) < 3:
		sys.exit(__doc__)
	img = Image(sys.argv[1])
	for arg in sys.argv[2:]:
		va = int(arg, 0)
		here = img.string(va)
		val = img.dword(va)
		there = img.string(val) if val else None
		out = '  0x%08x' % va
		if val is not None:
			out += '  = 0x%08x' % val
		if there:
			out += '  -> "%s"' % there
		elif here:
			out += '  "%s"' % here
		elif val is None:
			out += '  (not in any initialised section)'
		print(out)


if __name__ == '__main__':
	main()
