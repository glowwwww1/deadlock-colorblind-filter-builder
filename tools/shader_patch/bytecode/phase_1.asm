ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[1], immediateIndexed
dcl_constantbuffer CB1[22], immediateIndexed
dcl_resource_texture2d (float,float,float,float) t0
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 6
ftoi r0.xy, v0.xyxx
ftoi r0.zw, cb1[20].zzzw
iadd r0.zw, r0.zzzw, l(0, 0, -1, -1)
mov r1.zw, l(0,0,0,0)
mov r2.xyz, l(1000000.000000,0,0,0)
mov r3.y, l(-1)
loop
  ilt r2.w, l(1), r3.y
  breakc_nz r2.w
  mov r4.xyz, r2.xyzx
  mov r3.x, l(-1)
  loop
    ilt r2.w, l(1), r3.x
    breakc_nz r2.w
    imad r3.zw, r3.xxxy, cb0[0].xxxx, r0.xxxy
    imax r3.zw, r3.zzzw, l(0, 0, 0, 0)
    imin r1.xy, r0.zwzz, r3.zwzz
    ld_indexable(texture2d)(float,float,float,float) r5.yz, r1.xyzw, t0.zxyw
    mad r1.xy, v0.xyxx, cb1[21].xyxx, -r5.yzyy
    mul r1.xy, r1.xyxx, cb1[20].zwzz
    dp2 r5.x, r1.xyxx, r1.xyxx
    ge r1.xy, r5.yzyy, l(0.000000, 0.000000, 0.000000, 0.000000)
    and r1.x, r1.y, r1.x
    ge r1.y, r4.x, r5.x
    and r1.x, r1.y, r1.x
    movc r4.xyz, r1.xxxx, r5.xyzx, r4.xyzx
    iadd r3.x, r3.x, l(1)
  endloop
  mov r2.xyz, r4.xyzx
  iadd r3.y, r3.y, l(1)
endloop
mov o0.xy, r2.yzyy
mov o0.zw, l(0,0,0,0)
ret
