### Every `_is_wall_recess` call that reaches the back-edge test (a collinear-gap candidate past the other gates)

| sheet (f) | component | area px² | ground truth | th | gap cover | depth (bands) | back (extent) | extent verdict | face / gap | caps / gap | face / own | caps / own | dropped today |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s01 (0.542) | (810,980)–(846,1076) | 3393 | unmatched | 19.25px = 301mm | 0.860 | 1.83 | -2.00 | recess | 0.960 | 0.960 | 1.000 | 1.000 | yes |
| s05 (0.5) | (1587,468)–(1622,551) | 2908 | unmatched | 12.00px = 203mm | 0.795 | 2.94 | -2.00 | recess | 0.954 | 0.954 | 1.000 | 1.000 | yes |
| s05 (0.5) | (1569,1264)–(1593,1293) | 693 | unmatched | 27.50px = 466mm | 0.855 | 0.85 | -2.00 | recess | 1.000 | 1.000 | 1.000 | 1.000 | yes |
| s05 (0.5) | (1569,1311)–(1593,1340) | 693 | unmatched | 27.50px = 466mm | 0.855 | 0.85 | -2.00 | recess | 1.000 | 1.000 | 1.000 | 1.000 | yes |
| s05 (0.5) | (1569,1436)–(1593,1465) | 693 | unmatched | 27.50px = 466mm | 0.855 | 0.85 | -2.00 | recess | 1.000 | 1.000 | 1.000 | 1.000 | yes |
| s10 (1) | (497,2935)–(611,3026) | 6131 | false_positive | 32.23px = 273mm | 0.930 | 1.94 | -2.12 | recess | 1.000 | 1.000 | 1.000 | 1.000 | yes |
| s11 (0.5) | (781,1509)–(823,1533) | 1016 | false_positive | 17.63px = 299mm | 0.760 | 2.39 | -2.00 | recess | 0.858 | 0.858 | 1.000 | 1.000 | yes |
| s11 (0.5) | (886,874)–(976,917) | 3814 | unmatched | 17.63px = 299mm | 0.849 | 2.41 | -2.00 | recess | 0.957 | 0.957 | 1.000 | 1.000 | yes |
| s11 (0.5) | (1930,868)–(2001,899) | 2192 | false_positive | 17.63px = 299mm | 0.839 | 1.75 | -2.00 | recess | 0.947 | 0.947 | 1.000 | 1.000 | yes |
| s14 (1) | (2608,2022)–(2664,2110) | 4746 | false_positive | 35.50px = 301mm | 0.940 | 2.48 | -2.00 | recess | 1.000 | 1.000 | 1.000 | 1.000 | yes |
| s16 (0.5) | (1060,955)–(1149,998) | 3798 | unmatched | 17.62px = 298mm | 0.849 | 2.41 | -2.00 | recess | 0.957 | 0.957 | 1.000 | 1.000 | yes |
| s16 (0.5) | (2144,941)–(2215,972) | 2192 | false_positive | 17.63px = 299mm | 0.839 | 1.75 | -2.00 | recess | 0.947 | 0.947 | 1.000 | 1.000 | yes |
| s17 (1) | (1548,2766)–(1569,2910) | 3034 | unmatched | 13.25px = 112mm | 0.759 | 1.58 | -2.00 | recess | 0.893 | 0.893 | 1.000 | 1.000 | yes |
| s18 (0.5) | (2096,2506)–(2157,2558) | 3183 | false_positive | 17.75px = 301mm | 0.656 | 2.92 | -2.00 | recess | 0.739 | 0.739 | 1.000 | 1.000 | yes |

Calls corpus-wide: 72; with a candidate: 14; without (held out by the intersect / opening / gap-cover / depth gates, both readings False): 58.

### Calls per sheet

| sheet (f) | recess calls | with a candidate | dropped today | emitted rooms | rooms with a candidate |
|---|---|---|---|---|---|
| s01 (0.542) | 1 | 1 | 1 | 10 | 0 |
| s02 (1) | 0 | 0 | 0 | 11 | 0 |
| s03 (1) | 2 | 0 | 0 | 19 | 0 |
| s04 (1) | 0 | 0 | 0 | 6 | 0 |
| s05 (0.5) | 6 | 4 | 4 | 10 | 0 |
| s06 (0.5) | 0 | 0 | 0 | 9 | 0 |
| s07 (0.5) | 1 | 0 | 0 | 6 | 0 |
| s08 (1) | 1 | 0 | 0 | 3 | 0 |
| s09 (1) | 0 | 0 | 0 | 0 | 0 |
| s10 (1) | 1 | 1 | 1 | 9 | 0 |
| s11 (0.5) | 12 | 3 | 3 | 24 | 0 |
| s12 (0.5) | 8 | 0 | 0 | 13 | 0 |
| s13 (0.367) | 0 | 0 | 0 | 11 | 0 |
| s14 (1) | 1 | 1 | 1 | 0 | 0 |
| s15 (1) | 5 | 0 | 0 | 16 | 0 |
| s16 (0.5) | 13 | 2 | 2 | 29 | 0 |
| s17 (1) | 8 | 1 | 1 | 31 | 0 |
| s18 (0.5) | 12 | 1 | 1 | 24 | 0 |
| s19 (1) | 0 | 0 | 0 | 0 | 0 |
| s20 (1) | 1 | 0 | 0 | 5 | 0 |

### Emitted rooms that reach a candidate (the true class the back edge would decide)

None on any sheet: every emitted room is held out by the intersect / opening / gap-cover / depth gates before the back edge is read.

### The rule AS IMPLEMENTED under each runs reading (rooms diffed against the unmodified chain, scored)

| sheet (f) | base score (lost / returned FPs / unreviewed) | face_gap | caps_gap | face_own | caps_own |
|---|---|---|---|---|---|
| s01 (0.542) | 0 / 0 / 0 | identical | identical | identical | identical |
| s02 (1) | 12 / 0 / 0 | identical | identical | identical | identical |
| s03 (1) | 0 / 0 / 0 | identical | identical | identical | identical |
| s04 (1) | 0 / 2 / 0 | identical | identical | identical | identical |
| s05 (0.5) | 0 / 1 / 0 | identical | identical | identical | identical |
| s06 (0.5) | 0 / 0 / 0 | identical | identical | identical | identical |
| s07 (0.5) | 0 / 0 / 0 | identical | identical | identical | identical |
| s08 (1) | 0 / 1 / 0 | identical | identical | identical | identical |
| s09 (1) | 0 / 0 / 0 | identical | identical | identical | identical |
| s10 (1) | 0 / 0 / 0 | identical | identical | identical | identical |
| s11 (0.5) | 0 / 4 / 0 | identical | identical | identical | identical |
| s12 (0.5) | 0 / 5 / 0 | identical | identical | identical | identical |
| s13 (0.367) | 0 / 0 / 0 | identical | identical | identical | identical |
| s14 (1) | 0 / 1 / 0 | identical | identical | identical | identical |
| s15 (1) | 0 / 7 / 0 | identical | identical | identical | identical |
| s16 (0.5) | 0 / 10 / 0 | identical | identical | identical | identical |
| s17 (1) | 0 / 6 / 0 | identical | identical | identical | identical |
| s18 (0.5) | 0 / 22 / 0 | identical | identical | identical | identical |
| s19 (1) | 0 / 0 / 0 | identical | identical | identical | identical |
| s20 (1) | 0 / 1 / 0 | identical | identical | identical | identical |

(s02's 12 'lost' are the harness's omitted labels and schedule, as in every step's census; the sweep reads s02 15/15 doors, 11/11 rooms, 11/11 windows, 11/11 labels, 1/1 schedule.)
