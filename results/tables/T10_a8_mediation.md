### T10. A8 (EXPLORATORY, observational association): OLS of seed RF on standardized metrics + level dummies; cluster bootstrap over seeds. n = 38 (excluded 2 with undefined EAR); R² levels only 0.927, joint 0.978; VIF ear 1.4, rsr_other 1.3, tdi 1.7, pss 7.8, gini_consumption 1.4, cr 8.3

| model   | term             | coef_ci                    | within_level_spearman                                         |
|:--------|:-----------------|:---------------------------|:--------------------------------------------------------------|
| joint   | intercept        | 0.5306 [0.4812, 0.5889]    |                                                               |
| joint   | ear              | -0.0027 [-0.0235, 0.0081]  |                                                               |
| joint   | rsr_other        | -0.0006 [-0.0178, 0.0275]  |                                                               |
| joint   | tdi              | -0.0022 [-0.0272, 0.0214]  |                                                               |
| joint   | pss              | 0.0455 [0.0143, 0.0738]    |                                                               |
| joint   | gini_consumption | -0.0126 [-0.0279, 0.0088]  |                                                               |
| joint   | cr               | 0.0261 [-0.0163, 0.0913]   |                                                               |
| joint   | level_Moderate   | -0.2407 [-0.2880, -0.2013] |                                                               |
| joint   | level_Scarce     | -0.3311 [-0.4252, -0.2408] |                                                               |
| joint   | level_Critical   | -0.3518 [-0.4613, -0.2347] |                                                               |
| single  | ear              | 0.0172 [-0.0008, 0.0290]   | Abundant:0.333;Moderate:0.576;Scarce:0.000;Critical:-0.217    |
| single  | rsr_other        | -0.0223 [-0.0387, -0.0047] | Abundant:-0.576;Moderate:-0.236;Scarce:0.167;Critical:-0.017  |
| single  | tdi              | -0.0260 [-0.0456, -0.0112] | Abundant:-0.697;Moderate:0.103;Scarce:-0.633;Critical:-0.917  |
| single  | pss              | 0.0650 [0.0456, 0.0906]    | Abundant:0.952;Moderate:0.952;Scarce:0.800;Critical:0.400     |
| single  | gini_consumption | -0.0200 [-0.0615, -0.0045] | Abundant:-0.855;Moderate:-0.212;Scarce:-0.617;Critical:-0.583 |
| single  | cr               | 0.0824 [0.0537, 0.1200]    | Abundant:0.952;Moderate:0.733;Scarce:0.450;Critical:0.283     |
