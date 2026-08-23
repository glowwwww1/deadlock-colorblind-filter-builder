ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[22], immediateIndexed
dcl_resource_texture2d (float,float,float,float) t0
dcl_resource_texture2d (float,float,float,float) t1
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 5
ftoi r0.xy, v0.xyxx
mov r0.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.x, r0.xyww, t1.xyzw
eq r1.y, r1.x, l(0.000000)
ge r1.z, r1.x, l(0.509804)
or r1.y, r1.z, r1.y
if_nz r1.y
  mov o0.xyzw, l(0,0,0,0)
  ret
endif
ftoi r2.xyzw, cb0[20].zwzw
iadd r2.xyzw, r2.xyzw, l(-1, -1, -1, -1)
mul r1.yz, v0.xxyx, cb0[21].xxyx
ld_indexable(texture2d)(float,float,float,float) r0.z, r0.xyzw, t0.yzxw
iadd r3.xyzw, r0.xyxy, l(-1, -1, 0, -1)
imax r3.xyzw, r3.xyzw, l(0, 0, 0, 0)
imin r3.xyzw, r2.zwxy, r3.zwxy
mov r4.xy, r3.zwzz
mov r4.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.w, r4.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r1.w, r4.xyzw, t0.yzwx
ne r4.x, r1.x, r0.w
lt r0.w, r0.w, l(0.509804)
ge r1.w, r0.z, r1.w
or r0.w, r0.w, r1.w
and r0.w, r4.x, r0.w
and r0.w, r0.w, l(1)
mov r3.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.w, r3.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r3.x, r3.xyzw, t0.xyzw
ne r3.y, r1.x, r1.w
lt r1.w, r1.w, l(0.509804)
ge r3.x, r0.z, r3.x
or r1.w, r1.w, r3.x
iadd r1.w, r0.w, -r1.w
movc r0.w, r3.y, r1.w, r0.w
iadd r3.xyzw, r0.xyxy, l(1, -1, -1, 0)
imax r3.xyzw, r3.xyzw, l(0, 0, 0, 0)
imin r3.xyzw, r2.zwxy, r3.zwxy
mov r4.xy, r3.zwzz
mov r4.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.w, r4.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r4.x, r4.xyzw, t0.xyzw
ne r4.y, r1.x, r1.w
lt r1.w, r1.w, l(0.509804)
ge r4.x, r0.z, r4.x
or r1.w, r1.w, r4.x
iadd r1.w, r0.w, -r1.w
movc r0.w, r4.y, r1.w, r0.w
mov r3.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.w, r3.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r3.x, r3.xyzw, t0.xyzw
ne r3.y, r1.x, r1.w
lt r1.w, r1.w, l(0.509804)
ge r3.x, r0.z, r3.x
or r1.w, r1.w, r3.x
iadd r1.w, r0.w, -r1.w
movc r0.w, r3.y, r1.w, r0.w
iadd r3.xyzw, r0.xyxy, l(1, 0, -1, 1)
imax r3.xyzw, r3.xyzw, l(0, 0, 0, 0)
imin r3.xyzw, r2.zwxy, r3.zwxy
mov r4.xy, r3.zwzz
mov r4.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.w, r4.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r4.x, r4.xyzw, t0.xyzw
ne r4.y, r1.x, r1.w
lt r1.w, r1.w, l(0.509804)
ge r4.x, r0.z, r4.x
or r1.w, r1.w, r4.x
iadd r1.w, r0.w, -r1.w
movc r0.w, r4.y, r1.w, r0.w
mov r3.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.w, r3.xyww, t1.yzwx
ld_indexable(texture2d)(float,float,float,float) r3.x, r3.xyzw, t0.xyzw
ne r3.y, r1.x, r1.w
lt r1.w, r1.w, l(0.509804)
ge r3.x, r0.z, r3.x
or r1.w, r1.w, r3.x
iadd r1.w, r0.w, -r1.w
movc r0.w, r3.y, r1.w, r0.w
iadd r3.xyzw, r0.xyxy, l(0, 1, 1, 1)
imax r3.xyzw, r3.xyzw, l(0, 0, 0, 0)
imin r2.xyzw, r2.zwxy, r3.zwxy
mov r3.xy, r2.zwzz
mov r3.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.x, r3.xyww, t1.xyzw
ld_indexable(texture2d)(float,float,float,float) r0.y, r3.xyzw, t0.yxzw
ne r1.w, r1.x, r0.x
lt r0.x, r0.x, l(0.509804)
ge r0.y, r0.z, r0.y
or r0.x, r0.y, r0.x
iadd r0.x, -r0.x, r0.w
movc r0.x, r1.w, r0.x, r0.w
mov r2.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.y, r2.xyww, t1.yxzw
ld_indexable(texture2d)(float,float,float,float) r0.w, r2.xyzw, t0.yzwx
ne r1.x, r1.x, r0.y
lt r0.y, r0.y, l(0.509804)
ge r0.z, r0.z, r0.w
or r0.y, r0.z, r0.y
iadd r0.y, -r0.y, r0.x
movc r0.x, r1.x, r0.y, r0.x
ige r0.x, r0.x, l(3)
and o0.xy, r1.yzyy, r0.xxxx
mov o0.zw, l(0,0,0,0)
ret
