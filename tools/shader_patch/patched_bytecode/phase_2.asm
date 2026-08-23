ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[2], immediateIndexed
dcl_constantbuffer CB1[21], immediateIndexed
dcl_constantbuffer CB2[297], dynamicIndexed
dcl_resource_texture2d (float,float,float,float) t0
dcl_resource_texture2d (float,float,float,float) t1
dcl_resource_structured t2, 8
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 3
ftoi r0.xy, v0.xyxx
mov r0.zw, l(0,0,0,0)
ld_indexable(texture2d)(float,float,float,float) r1.xy, r0.xyww, t1.xyzw
mul r1.z, r1.y, r1.x
ne r1.z, r1.z, l(0.000000)
and r1.z, r1.z, l(1)
if_nz r1.z
  mul r1.xz, r1.xxyx, cb1[20].zzwz
  ftoi r2.xy, r1.xzxx
  mov r2.zw, l(0,0,0,0)
  ld_indexable(texture2d)(float,float,float,float) r1.x, r2.xyzw, t0.xyzw
  ld_indexable(texture2d)(float,float,float,float) r0.z, r0.xyzw, t0.yzxw
  eq r0.z, r0.z, r1.x
  movc r0.z, r0.z, l(-0.250000), l(0.250000)
  mul r0.w, r1.x, l(255.000000)
  ftoi r0.w, r0.w
  imax r0.w, r0.w, l(0)
  imin r0.w, r0.w, l(127)
  ige r1.x, r0.w, l(2)
  iadd r1.z, r0.w, l(-2)
  movc r1.w, r1.x, cb2[r1.z + 171].y, cb0[0].y
  iadd r0.xy, -r0.xyxx, r2.xyxx
  itof r0.xy, r0.xyxx
  dp2 r0.x, r0.xyxx, r0.xyxx
  sqrt r0.x, r0.x
  mul r0.y, r1.w, cb0[0].z
  mad r0.x, r0.x, r0.z, -r0.y
  add_sat r0.x, -|r0.x|, r1.w
  lt r0.y, l(0.000000), cb0[1].x
  and r0.y, r0.y, r1.x
  ld_structured_indexable(structured_buffer, stride=8)(mixed,mixed,mixed,mixed) r1.xz, r1.z, l(0), t2.xxyx
  itof r1.xz, r1.xxzx
  mul r2.xy, r1.xzxx, l(0.000015, 0.000015, 0.000000, 0.000000)
  lt r0.z, r2.x, r2.y
  mad r1.y, r1.y, l(2.000000), l(-1.000000)
  mad r1.x, -r1.x, l(0.000015), -r1.y
  mad r1.y, r1.z, l(0.000015), -r2.x
  div_sat r1.x, r1.x, r1.y
  log r1.x, r1.x
  mul r1.x, r1.x, cb0[1].x
  exp r1.x, r1.x
  mul r1.x, r0.x, r1.x
  movc r0.z, r0.z, r1.x, r0.x
  movc r0.x, r0.y, r0.z, r0.x
  mul r0.x, r0.x, cb0[0].w
  mul o0.xyzw, r0.xxxx, cb2[r0.w + 42].xyzw
else
  mov o0.xyzw, l(0,0,0,0)
endif
ret
