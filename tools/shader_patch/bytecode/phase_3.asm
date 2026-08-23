ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[22], immediateIndexed
dcl_resource_texture2d (float,float,float,float) t0
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 4
resinfo_indexable(texture2d)(float,float,float,float) r0.xy, l(0), t0.xyzw
div r0.zw, v0.xxxy, cb0[21].zzzw
mul r0.xy, r0.xyxx, r0.zwzz
ftoi r0.xy, r0.xyxx
mov r0.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.z, r0.xyzw, t0.yzxw
mul r0.z, r0.z, l(255.000000)
ftoi r0.z, r0.z
ieq r0.w, r0.z, l(0)
ige r0.z, r0.z, l(130)
or r0.z, r0.z, r0.w
movc r0.z, r0.z, l(0), l(1.000000)
iadd r1.xyzw, r0.xyxy, l(0, 1, 1, 0)
iadd r2.xy, r0.xyxx, l(1, 1, 0, 0)
mov r3.xy, r1.zwzz
mov r3.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.x, r3.xyzw, t0.xyzw
mul r0.x, r0.x, l(255.000000)
ftoi r0.x, r0.x
ieq r0.y, r0.x, l(0)
ige r0.x, r0.x, l(130)
or r0.x, r0.x, r0.y
movc r0.x, r0.x, l(0), l(1.000000)
add r0.x, r0.x, r0.z
mov r1.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.y, r1.xyzw, t0.yxzw
mul r0.y, r0.y, l(255.000000)
ftoi r0.y, r0.y
ieq r0.z, r0.y, l(0)
ige r0.y, r0.y, l(130)
or r0.y, r0.y, r0.z
movc r0.y, r0.y, l(0), l(1.000000)
add r0.x, r0.y, r0.x
mov r2.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r0.y, r2.xyzw, t0.yxzw
mul r0.y, r0.y, l(255.000000)
ftoi r0.y, r0.y
ieq r0.z, r0.y, l(0)
ige r0.y, r0.y, l(130)
or r0.y, r0.y, r0.z
movc r0.y, r0.y, l(0), l(1.000000)
add r0.x, r0.y, r0.x
ge r0.y, r0.x, l(3.990000)
ge r0.x, l(0.000000), r0.x
movc r0.y, r0.y, l(1.000000), l(0.500000)
movc o0.xyzw, r0.xxxx, l(0,0,0,0), r0.yyyy
ret
