ps_5_0
dcl_globalFlags refactoringAllowed
dcl_constantbuffer CB0[22], immediateIndexed
dcl_sampler s0, mode_default
dcl_resource_texture2d (float,float,float,float) t0
dcl_input_ps_siv linear noperspective v0.xy, position
dcl_output o0.xyzw
dcl_temps 1
div r0.xy, v0.xyxx, cb0[21].zwzz
sample_l_indexable(texture2d)(float,float,float,float) r0.x, r0.xyxx, t0.xyzw, s0, l(0.000000)
eq r0.x, r0.x, l(0.000000)
discard_nz r0.x
mov o0.xyzw, l(0,0,0,0)
ret
