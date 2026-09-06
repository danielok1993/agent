### Every `_is_band_pocket` call at or under 56 × f

| sheet (f) | component | spacing | ground truth | (a) inside | (b) solid behind each side | (c) pens | covers (shipped) | (d) end closures | note |
|---|---|---|---|---|---|---|---|---|---|
| s17 (1) | (3434,2186)–(3579,2207) | 25.25 = 214mm | unmatched | no text, 0 glyph strokes | 0.00 / 1.00 (spans 11.2 / 0.0px) | same | 1.00 / 1.00 | **0.00 / 1.00** | dropped today |
| s17 (1) | (912,2174)–(947,2331) | 38.75 = 328mm | false_positive | no text, 0 glyph strokes | 0.12 / 0.21 (spans 0.0 / 0.0px) | same | 0.99 / 1.00 | **0.00 / 0.34** | kept today |
| s17 (1) | (914,2609)–(949,3061) | 38.75 = 328mm | false_positive | no text, 0 glyph strokes | 0.08 / 0.11 (spans 0.0 / 0.0px) | same | 1.00 / 1.00 | **0.14 / 0.34** | kept today |
| s17 (1) | (3047,2174)–(3084,2489) | 38.79 = 328mm | false_positive | no text, 0 glyph strokes | 0.16 / 0.20 (spans 0.0 / 0.0px) | same | 0.96 / 0.99 | **0.00 / 0.00** | kept today |
| s17 (1) | (3047,2594)–(3084,3061) | 40.50 = 343mm | false_positive | no text, 0 glyph strokes | 0.10 / 0.11 (spans 0.0 / 0.0px) | same | 1.00 / 1.00 | **0.00 / 0.00** | kept today |
| s18 (0.5) | (2079,1023)–(2096,1068) | 21.25 = 360mm | false_positive | no text, 0 glyph strokes | 0.00 / 0.04 (spans 0.0 / 0.0px) | same | 0.86 / 1.00 | **0.00 / 0.29** | kept today |
| s11 (0.5) | (1078,1597)–(1095,1704) | 21.75 = 368mm | confirmed | no text, 0 glyph strokes | 0.00 / 1.00 (spans 0.0 / 5.1px) | same | 1.00 / 1.00 | **1.00 / 1.00** | kept today |
| s16 (0.5) | (2507,1323)–(2527,1401) | 24.00 = 406mm | false_positive | no text, 0 glyph strokes | 0.00 / 0.00 (spans 0.0 / 0.0px) | same | 1.00 / 1.00 | **1.00 / 1.00** | kept today |
| s12 (0.5) | (1842,472)–(1873,494) | 26.13 = 442mm | false_positive | no text, 0 glyph strokes | 0.09 / 1.00 (spans 11.0 / 2.0px) | different | 1.00 / 1.00 | **0.00 / 1.00** | kept today |
| s18 (0.5) | (907,810)–(1079,833) | 27.25 = 462mm | false_positive | no text, 0 glyph strokes | 0.00 / 0.00 (spans 0.0 / 0.0px) | same | 0.90 / 1.00 | **0.00 / 0.72** | kept today |
| s12 (0.5) | (1842,530)–(1873,554) | 27.75 = 470mm | false_positive | no text, 0 glyph strokes | 0.00 / 1.00 (spans 1.8 / 5.2px) | same | 0.94 / 1.00 | **0.00 / 1.00** | kept today |

### Every confirmed room at or under 72 × f (the true class, entered or not)

| sheet (f) | component | spacing | ground truth | (a) inside | (b) solid behind each side | (c) pens | covers (shipped) | (d) end closures | note |
|---|---|---|---|---|---|---|---|---|---|
| s11 (0.5) | (1078,1597)–(1095,1704) | 21.75 = 368mm | confirmed | no text, 0 glyph strokes | 0.00 / 1.00 (spans 0.0 / 5.1px) | same | 1.00 / 1.00 | **1.00 / 1.00** | entrances 0, doors 0, windows 0 |
| s17 (1) | (628,3056)–(905,3119) | 67.10 = 568mm | confirmed | no text, 0 glyph strokes | 0.56 / 0.61 (spans 35.0 / 11.2px) | same | 0.61 / 0.61 | **0.72 / 0.72** | entrances 2, doors 2, windows 0 |
| s20 (1) | (554,2812)–(948,2878) | 70.75 = 599mm | confirmed | no text, 0 glyph strokes | 0.00 / 1.00 (spans 0.0 / 35.0px) | same | 1.00 / 1.00 | **0.00 / 1.00** | entrances 0, doors 0, windows 0 |
| s15 (1) | (766,1549)–(833,1669) | 71.00 = 601mm | confirmed | no text, 0 glyph strokes | 0.00 / 1.00 (spans 11.2 / 0.0px) | same | 1.00 / 1.00 | **0.50 / 1.00** | entrances 0, doors 0, windows 0 |
| s07 (0.5) | (454,190)–(486,290) | 36.00 = 610mm | confirmed | no text, 0 glyph strokes | 0.00 / 0.00 (spans 0.0 / 0.0px) | same | 1.00 / 1.00 | **0.06 / 0.06** | entrances 0, doors 0, windows 0 |

calls 58, emitted rooms 244 (187 confirmed); calls enclosed at both ends (>= 0.65): 17
    ('s05', [1851.8, 1261.3, 1894.8, 1417.3], 'false_positive')
    ('s05', [1921.6, 782.8, 2065.8, 1056.5], 'confirmed')
    ('s08', [1463.2, 1060.1, 1677.7, 1130.6], 'confirmed')
    ('s11', [1077.5, 1597.0, 1095.2, 1704.0], 'confirmed')
    ('s12', [1970.6, 1434.5, 2013.3, 1478.8], 'false_positive')
    ('s12', [1972.6, 1322.8, 2013.3, 1417.5], 'false_positive')
    ('s12', [1870.1, 811.3, 2014.3, 1101.7], 'confirmed')
    ('s15', [648.9, 956.4, 832.9, 1058.7], 'confirmed')
    ('s15', [436.4, 979.9, 633.2, 1058.7], 'confirmed')
    ('s15', [1291.4, 973.7, 1441.2, 1045.7], 'false_positive')
    ('s15', [1022.2, 1425.2, 1441.2, 1495.7], 'false_positive')
    ('s16', [2479.2, 1322.8, 2503.3, 1401.3], 'false_positive')
    ('s16', [2507.3, 1322.8, 2527.3, 1401.3], 'false_positive')
    ('s17', [708.4, 2595.7, 802.9, 2876.4], 'confirmed')
    ('s18', [1660.0, 2092.7, 1708.0, 2159.2], 'confirmed')
    ('s18', [2178.7, 2093.2, 2493.2, 2540.5], 'false_positive')
    ('s18', [2178.7, 1219.2, 2245.0, 1276.7], 'confirmed')
confirmed rooms by end closure (both ends >= 0.65): {'open-ended': 110, 'enclosed': 77}
