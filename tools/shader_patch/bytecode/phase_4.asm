ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[22], immediateIndexed
dcl_sampler s0, mode_default
dcl_resource_texture2d (float,float,float,float) t0
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 1
div r0.xy, v0.xyxx, cb0[21].zwzz
sample_l_aoffimmi_indexable(-1,-1,0)(texture2d)(float,float,float,float) r0.z, r0.xyxx, t0.yzxw, s0, l(0.000000)
sample_l_aoffimmi_indexable(1,-1,0)(texture2d)(float,float,float,float) r0.w, r0.xyxx, t0.yzwx, s0, l(0.000000)
add r0.z, r0.w, r0.z
sample_l_aoffimmi_indexable(1,1,0)(texture2d)(float,float,float,float) r0.w, r0.xyxx, t0.yzwx, s0, l(0.000000)
sample_l_aoffimmi_indexable(-1,1,0)(texture2d)(float,float,float,float) r0.x, r0.xyxx, t0.xyzw, s0, l(0.000000)
add r0.y, r0.w, r0.z
add r0.x, r0.x, r0.y
ge r0.y, r0.x, l(3.990000)
eq r0.x, r0.x, l(0.000000)
movc r0.y, r0.y, l(1.000000), l(0.500000)
movc o0.xyzw, r0.xxxx, l(0,0,0,0), r0.yyyy
ret
