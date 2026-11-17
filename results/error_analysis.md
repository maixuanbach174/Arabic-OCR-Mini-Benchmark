# Error analysis

The 15 worst predictions per system (appendix) are dominated by total failures: empty output for the classic engines and runaway generations for Qwen. They say *that* a system failed, not *how* it misreads Arabic. So the analysis has two parts:

1. **Catastrophic failure modes**, counted automatically over all 300 predictions per system (`src/errors.py: failure_flags`).
2. **Arabic-specific error types**, hand-labelled on 15 randomly sampled partial errors per system (5% < normalized CER ≤ 60%). The labels and a one-line note per sample are in `results/error_labels.csv`.

## Findings

**The VLM and the classic engines fail in different ways.**

- **Qwen2.5-VL-3B makes word-level errors.** In 12 of its 15 sampled errors it writes a *real, fluent Arabic word that is not in the image* (ابتدات→البدلات, المريخ→المرجح, الكلمات→الاتصالات). On KHATT's nonsense test words (مشمش، غيظ، بث) it substitutes real words (مشهدة، عيال، بنت). The output reads well, so these errors are hard to catch downstream.
- **Its language prior surfaces in two other ways.** It completes formulae that are cut off in the image (adds وسلم after صلى الله عليه, pats_0279). On illegible manuscript lines it falls back on religious phrases (الله لا إله إلا هو, الحمد لله) that are not on the page: 12 of the 100 HistoryAr outputs, 4 of which then loop until they hit the 256-token cap. In total, 7 of 300 Qwen outputs hit that cap. On HistoryAr, 10% of outputs run past 1.5× the reference length, which is why its mean CER there is 157% while the median is 39%.
- **It also adds diacritics that are not in the image.** 67 of 100 KHATT outputs carry tashkeel, but only 6 KHATT references do. That is why normalization cuts Qwen's median CER by 23 points on KHATT and 27 on HistoryAr, but cuts the classic engines' by only 0–11.
- **It produced 2 non-Arabic outputs.** One PATS line came back mostly in Chinese (pats_0116), and one historical line came back as a LaTeX fraction.

- **Tesseract makes character-level errors.** Its errors are letter-shape confusions (13 of 15) and dotted-letter confusions (9 of 15): ت→ن, ف→ق, ه→ة, ي→ب. These are exactly the pairs that share a skeleton (rasm) and differ only in dots. When it cannot read a line at all, it returns **nothing**: 80 of 300 lines (51% of HistoryAr, 23% of KHATT, and even 6% of clean PATS lines) come back empty. On a line I probed, grayscaling, contrast stretching and halving the resolution all still gave empty output, which points to a recognition failure rather than a preprocessing bug.

- **EasyOCR makes segmentation errors.** 9 of its 15 errors merge or split words (وبيلانالجزءالثالت = four words glued together). It also injects Latin digits and symbols (`7`, `=`, `_`) into Arabic text, and its CRAFT detector misses short historical fragments (9% empty on HistoryAr).

**Dotted-letter confusion is common to all three** (Qwen 5 of 15, Tesseract 9, EasyOCR 8). It is the one Arabic-specific error no system has solved, but for the VLM it is not the dominant one.

**Reference noise.** Some HistoryAr references are page numbers (٧٢), marginal notes (صح) or contain stray brackets (`ا[؟`). Several use dotless manuscript letters (ٮ, ٯ, ڡ, ں). `ڡ`/`ں` are mapped in normalized mode; dotless `ٮ` is left as is because it can stand for ب, ت, ث, ن or ي.


## 1. Catastrophic failure modes

Counted over all 300 predictions per system.

| Failure mode | Qwen2.5-VL-3B (MLX) | Tesseract 5 (ara) | EasyOCR (ar) |
|---|---:|---:|---:|
| Empty output | 0 | 80 | 9 |
| Output > 1.5x reference length | 14 | 0 | 0 |
| Repetition loop (a 3-gram repeated 3+ times) | 6 | 0 | 0 |
| Mostly non-Arabic script (e.g. Chinese, Latin) | 2 | 0 | 0 |
| Religious formula not in the image (الله لا إله إلا هو / الحمد لله) | 12 | 0 | 0 |

## 2. Arabic-specific error types

15 randomly sampled predictions per system (seed 42) with 5% < CER ≤ 60%, i.e. partial misreadings rather than total failures; hand-reviewed labels (`results/error_labels.csv`). A sample can carry several labels.

| Error type | Qwen2.5-VL-3B (MLX) | Tesseract 5 (ara) | EasyOCR (ar) |
|---|---:|---:|---:|
| Confused dotted letters (ب/ت/ث, ج/ح/خ, ...) | 5 | 9 | 8 |
| Other letter-shape confusion (e.g. ع/ه, ر/و, م/ه) | 2 | 13 | 6 |
| Whole-word substitution (a real but wrong word) | 12 | 0 | 0 |
| Letter joining / word segmentation (merged or split words) | 5 | 5 | 9 |
| Digit errors | 1 | 0 | 4 |
| Word order or right-to-left reversal | 1 | 0 | 0 |
| Missing words | 1 | 2 | 6 |
| Hallucinated / repeated text | 1 | 0 | 0 |
| Inserted words or punctuation | 2 | 4 | 3 |

## Labeled samples

### Qwen2.5-VL-3B (MLX)

| id | CER | labels | ground truth | prediction | note |
|---|---:|---|---|---|---|
| historyar_0059 | 28% | word, dotted, joining | برجه الميزان سٰاعته المريخ في الفلك الخامس يوم الثّلثاء وله | وجب الميزان ساعة المرجح في الضلك الخامس بومالك النداء ولد | المريخ→المرجح (real word); خ→ح; يوم الثلثاء merged into بومالك |
| historyar_0075 | 18% | word, shape | والحصٰار واختم بما وراء النّهر واذا ابتدات بالعراق فانتقل | واالحصار ولختمه مما داء النهر وإذا البدلات بالعراق فننتقل | ابتدات→البدلات: a real but wrong word |
| historyar_0097 | 28% | word, shape, digits | النابته في اعلي موضع من النبات شعبٌ دِقاق فى اطرَافِها | الناية 2 اعلى موضع من اللنات شعبه دقات خاطرها | اطرافها→خاطرها; invents the digit 2 |
| historyar_0163 | 17% | word, joining | له كوچك وهو رابع الُمقامات والزّنكو له طبعه هوائي | لَهُ كُرْجِلٌ وَهُوَ رَابِعُ الْمَقَامَاتِ وَالْنَّتَكُوْلَهُ طَبَعَهُ هَوَاءً | Persian کوچک→كرجل; والزنكو له merged |
| khatt_0041 | 38% | word, dotted | الكلمات التالية لهذا النص: مشمش , دراق , غيظ، ناء , بث , نس . | العلامات التالية لهذا العلم: مشهدة، دراق، عيال، ناد، بنت، نعمى. | Replaces the nonsense test words (مشمش، غيظ، بث) with real words (مشهدة، عيال، بنت) |
| khatt_0089 | 27% | word, joining | العهد ففيها فقرات كثيرة ن عم "وهب" أو آخرون قالوا ذلك على لسانه، | العهد فيها فقرات كثيرة نعم ونصب وأخذون فاللذ ذكر على لما س، | وهب→ونصب; ن عم→نعم |
| khatt_0090 | 44% | word, missing | في الحج. هل تعلم فائدة الكلمات التاليه # لهذا النص: مشمس، دراق | في الحج، هل تعلم فائدتك الاتصالات التالية؟، رأي | الكلمات→الاتصالات; drops the end of the line |
| khatt_0114 | 40% | word, extra | وهلال خازن عفيف للحج . بدأت قوافل الحجيج حاج إثر آخر يلبي | وَهُلَّادُ خَازَنُ عَذَبِ اللَّهِ . بَدَا تَحْوَافَ اللَّهِ بِبَحْرِ حَاجَةٍ إِلَّا أَنَّهُ يَلْبِي | Inserts الله where the image has للحج / الحجيج |
| khatt_0119 | 56% | word, hallucination | مؤثرة عند بداية الثورة الصناعية. إن تضاعف عدد سكان الكرة الأرضية | مُؤرِّقة حَسَنَ بِإيَّاهَا المُؤرَّقة المُنَاجِيَةِ . رَأَى كَثْرَةٌ حَسَنَ المُؤرَّقة إِلَّا، فَمَنْ | Fluent but unrelated text; repeats المؤرقة |
| khatt_0197 | 6% | dotted | أخرى. 3. # تطوير القدرة على المشاركة في الحياة الاجتماعية والثقافية والسياسية | أحرز. ٣. تطور القدرة على المشاركة في الحياة الاجتماعية والثقافية والسياسية | اخرى→احرز (خ→ح) |
| khatt_0198 | 9% | joining, word | السابقين عن الإدارة العامة إلا إنه لم يعد # هنالك شك في | السابقين عن الإدارة العامة إلا إنه لم يعر هنا لك شكر في | هنالك→هنا لك; شك→شكر |
| pats_0142 | 29% | order, word | قبل الخطبة ثم يخطب بعد خرج النبي صلى الله عليه وسلم كأني أنظر إليه حين يجلس بيده ثم | ثم يخطب بعد خروج النبي صلى الله عليه وسلم كأني أنظر إليه حين يجلس بيده ثم يقبل الخطبة | Moves قبل الخطبة to a different position; خرج→خروج |
| pats_0279 | 6% | extra | سالم وأبي بكر بن سليمان بن أبي حثمة أن عبد الله بن عمر قال صلى بنا النبي صلى الله عليه | سالم وأبي بكر بن سليمان بن أبي حثمة أن عبد الله بن عمر قال صلى بنا النبي صلى الله عليه وسلم | Adds وسلم: the language prior completes صلى الله عليه وسلم |
| pats_0325 | 7% | dotted, word, joining | مكانك ثم أتي به حتى جلس إلى جنبه قيل للأعمش وكان النبي صلى الله عليه وسلم يصلي وأبو بكر | مَا كَذَلِكَ ثُمَّ أَنْيَ بِهِ حَتَّى جَلَسَ إِلَى جَنَبِهِ قَيلَ لَلْأَعْمَشِ وَكَانَ النَّبِيُّ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ يَصْلِي فَأَبُو بَكْرٌ | اتى→انى (ت→ن); مكانك→ما كذلك |
| pats_0373 | 7% | dotted | بوله وكان الآخر يمشي بالنميمة ثم دعا بجريدة فكسرها كسرتين فوضع على كل قبر منهما كسرة | يوله وكان الآخر يشي بالثنيمة ثم دعا يجريدة فكسرها كسرتين فوضع على كل قبر منها كسرة | بوله→يوله; بجريدة→يجريدة (ب→ي); النميمة→الثنيمة |

### Tesseract 5 (ara)

| id | CER | labels | ground truth | prediction | note |
|---|---:|---|---|---|---|
| historyar_0006 | 32% | dotted, shape, joining | معَدل النهار وَالزوايَا ايضا | معرل| لنهاردالروانا ايض | الزوايا→الروانا (ز→ر، ي→ن); معدل→معرل (د→ر); النهار merged with next letter |
| historyar_0071 | 32% | joining, shape | وتكون كل واحدة من قوسي د ﺟ ز زحط ربع دايرة مِن اجْل ان افق | وتكوزجزواحرة مرو سم دج ز زحط ربع دايرة مزاج زافق | وتكون كل واحدة→وتكوزجزواحرة |
| khatt_0001 | 53% | shape, dotted | وهلال خازن عفيف للحج . بدأت قوافل الحجيج حاج إثر آخر يلبي | ع هصطلرا ل هارن عضي للمع .د ) ست مها فق المجيج ماه ور ني بلي | Letter soup on handwriting; خازن→هارن |
| khatt_0031 | 44% | shape, joining, extra | فألفو ذلك وقد هلك من العرب من هلك بالموت والقتل، فحفظوا أقل ذلك، وذهب | خا لعو ذ لك وم هلك اهرب من هللا را مي د و القتل؛ فُحمظ وا أ و[ لك ودص | Splits ذلك→ذ لك; stray punctuation |
| khatt_0075 | 20% | shape, joining | مما يؤدي الى بروز عصر مناخي جديد سماه العصر البشري. | مما يؤدي أ بروز عمر ملاخي جديد سماء الحمر ا لبر . | عصر→عمر (ص→م); مناخي→ملاخي; البشري→ا لبر |
| khatt_0082 | 45% | shape, dotted, missing | والعتبات وهنا تظهر المراوح الفيضية والهول الفيضية بدور عدد الاتصال. | زلبك مرهنا تلص الموج العيغيج امورل الميفية جدورعد الال | Garbled; drops words |
| khatt_0099 | 47% | shape, extra | امدا طويلا وأن آفات النسيان ونلاعب الزمان بالحفضـ لا بد ان يغير | مرا موسلا برا أعناع اسان ول زعم اعرامان ,| مف ل بد ان بعر | Garbled; stray | and commas |
| khatt_0120 | 53% | shape, extra | قضية تشغل حيزا كبيرا من اهتمامات الراي العام . وكان مؤتمر ستوكهولم للبيئة | دسرة تشمق صن لمرا من اويم| مان الراي الماح :دلا شنيو بوكر لير البرع | Garbled; stray | |
| khatt_0151 | 50% | shape, missing | في مجال الزراعه المستدامه متوسطا | ص مجال ارام اغرن تأيه متو يعدا | Garbled; drops words |
| khatt_0189 | 25% | dotted, shape | يتكلم وهو نائم بكلمات لا أفهمها مثل انقض بفلس له الضابط لزمتك. سألت راجح هل بلغ | يتكلم وو ناتم بكلات ل أفونا مئل إنقض بفلس (ه إداط لزيتلك . دالت راحم عل بل | نائم→ناتم; مثل→مئل; راجح→راحم; هل→عل |
| khatt_0198 | 26% | dotted, shape, extra | السابقين عن الإدارة العامة إلا إنه لم يعد # هنالك شك في | السابصسن عن الادارة العامة ألا إنه لم بعر هلل هتالك شرى قل : | يعد→بعر (ي→ب); هنالك→هتالك (ن→ت) |
| pats_0047 | 7% | dotted, joining | يعلمون ما فيهما لأتوهما ولو حبوا لقد هممت أن آمر المؤذن فيقيم ثم آمر رجلا يؤم الناس ثم | علمون ما فيهما لأنوهما ولوحبوا لد “ممت أن آمر المؤذن فيقيم ثم آمر رجلا يؤم الئاس ثم | لاتوهما→لانوهما (ت→ن); الناس→الئاس; ولو حبوا merged |
| pats_0309 | 11% | dotted | عن الصلاة بعد الفجر حتى تطلع الشمس وبعد العصر حتى تغرب الشمس وعن اشتمال الصماء وعن | عن الصلاة بعد النجسى حنى تطيع الشمس وبعد العص حنى تغرب الشمس معن أشثمال الصماء وعن | حتى→حنى twice (ت→ن); اشتمال→اشثمال (ت→ث) |
| pats_0447 | 14% | dotted, shape | وجاع العيال فادع الله لنا فرفع يديه وما نرى في السماء قزعة فوالذي نفسي بيده ما وضعها | وجالم العيال فادع الله لذا فرقع يدية وها نري ؤي السماء قؤعة فوالطذي نفسي بيذة ها وضعها | فرفع→فرقع (ف→ق); يديه→يدية (ه→ة); ما→ها |
| pats_0470 | 14% | dotted, shape | نعم ولولا مكاني منه ما شهدته يعني من صغره أتى العلم الذي عند دار كثير بن الصلت ثم خطب | عه ولولا مكاني هنة كا شعدتة يعني من صغره أتي العله الذي عند صار كُثير بن الصلت ثهو خط | شهدته→شعدتة (ه→ة); دار→صار; ما→كا |

### EasyOCR (ar)

| id | CER | labels | ground truth | prediction | note |
|---|---:|---|---|---|---|
| historyar_0007 | 28% | joining | الاول من الدّايره الٮى تمر على | لآولم الدايره الىترعل | الاول من→لاولم; التى تمر على→اليترعل |
| historyar_0067 | 33% | dotted, shape, missing | موَاضع فيها صخور وورق هَذا النبات اذا تصمّد به اللّحم الجراحا | مواضع فها محوز وورق هدا لسات اد الصمد بها الجماجرجا | صخور→محوز (خ→ح، ر→ز); هذا→هدا (ذ→د) |
| historyar_0108 | 41% | joining, dotted, digits | من مجموع الحواصل الزايدة يكن الجواب خمسة عشر درهما وخمسة وسبعين شيا وحمسة | محمبوعا حواصلالزابدة كنا جوابعسة عً تردرها رحسة وبعنش با7س | حواصلالزابدة merged; injects the digit 7 |
| historyar_0138 | 18% | joining | اجْزَاءِِ وَالأَرْبِعِ وَالأَرْبعِينَ دَقِيقَة وَالثّلاَثِ وَالخَمسِينَ ثَانِيةََ إِلَی الثّمانِيَّةِ | اجزًا ء والأربع والأربعيح قيقة والثادث والحخسبرثانيةً إلالثمانية | دقيقة split; والخمسين ثانية→والحخسبرثانية merged |
| historyar_0149 | 32% | joining, dotted, missing | مد وَ بيّنٌ انّ الجُزْءَ الثّالِثَ مِنَ الإِثْنَي | مد وبيلانالجزءًالثالتً مزالا | وبيلانالجزءالثالت: four words merged; ث→ت |
| historyar_0168 | 36% | joining, shape | دقىٯه وارٮعون ٮانىه ووترها ثمانىه وارٮعون جرا وَا̮حدى وٮلثون دقىٯه وحمسً | دقعه وارلعونانمد ووترهاثا ن~ وارلعوزجا واحدل وبلثون فعد ومس | وارلعونانمد merged; the reference uses dotless ٮ/ٯ |
| historyar_0178 | 21% | joining, dotted | لقلوبهم حٰالة السّمٰاع بالتلذّذ التّام واذا كنت بمجلس مع عوام | لقلوباء حالذالسماع بالنلذد التام واذاكت بجلسععوام | بجلسععوام merged; بالتلذذ→بالنلذد (ت→ن، ذ→د) |
| historyar_0197 | 41% | joining, dotted, missing | ان ىوتى بلفظ الجواب كلفط السؤال ففى قسمة شى على مال وقسمة ثلاثة اشيا على كعب مثلا | انبوتباً هطا جواب كلوط السوالدفف قسة سىعلالدقسمه ثلائه اسهاعا عبتتلا | شيء→سي (ش→س); ثلاثة→ثلائه |
| khatt_0004 | 30% | dotted, shape, extra | مثل أنقض بغـلس له الضابط لزمتك. سألت راجح هل أبلغ أصحابنا | مث ' نقحى نغلل لل الطا ط لرمرك سالت راجح هل ابل امجا بنا | لزمتك→لرمرك (ز→ر); انقض→نقحى |
| khatt_0039 | 51% | dotted, shape, digits | متوازن. وقد اتخذت مقاطع كتابة تشيان لونغ قوتها وحيويتها من السمات | لتون رحدا رمذت مفاب حتابم سمبان لونء حولها 9 حيوللما حرز ا لسا ن | Garbled; injects 9 |
| khatt_0093 | 40% | dotted, digits, joining | لا أفهمها مثل انقض بغـلس له الضابط لزمتك. سألت راجح هل بلغ أصحابنا ظ ع ك ، ت خ ض، | امامه متل ا لفآل بخلساب المابط لزمتك . رآلت رجح مل بلح ا صحاباظ ع ا6ك خص | مثل→متل (ث→ت); injects 6 |
| khatt_0188 | 60% | shape, digits, extra, missing | وكان الحصاد يتم بالأيدي والمناجل و فتخرج القرية أو العشيرة عن بكرة أبيها في الصباح | زكا ~ ا لحصاد الآير رالنا عل متحع الترر= أرالء 5 حمم بكسء 11 _-2 | Garbled with digits and symbols (= ~ _) |
| pats_0052 | 10% | missing, extra | على السرير فتكون لي الحاجة فأكره أن أستقبله فأنسل انسلالا وعن الأعمش عن إبراهيم عن | السرير فتكون _ الحاجة فأكره أن أستقبله _ فأنسل انسلالا وعن الأعمش عن إبراهيم عن | Drops على; emits underscores |
| pats_0112 | 8% | missing, shape | قال ابسط رداءك فبسطته قال فغرف بيديه ثم قال ضمه فضممته فما نسيت شيئا بعده حدثنا | قال اسط رداء فبسطته قال فغرف بيدىه قال ضمه فضممته فما نسيت شيئا لعده حدثنا | ابسط→اسط; drops ثم; بعده→لعده |
| pats_0316 | 6% | joining | يلقاه جبريل وكان يلقاه في كل ليلة من رمضان فيدارسه القرآن فلرسول الله صلى الله عليه وسلم | يلقاه جبريل وكان يلقاه فيكل ليلة من مضان فيدار ه سه القرآن فلرسول الله صلى الله عليه وسلم | في كل→فيكل; فيدارسه→فيدار ه سه |

## Appendix: worst 15 predictions per system

### Qwen2.5-VL-3B (MLX)

| id | CER | ground truth | prediction |
|---|---:|---|---|
| historyar_0053 | 2833% | ليْس فيها اعْوجَاج | اللهُ لا إلهَ إلا هو الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الحمدُ للهِ الح… |
| historyar_0039 | 2730% | فهو الراٮع وان كان الحط | الله لا إله إلا هو الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله الحمد لله ا… |
| historyar_0129 | 2713% | دلک الخط مرٮع خط ىشاركه | الله لا إله إلا هو الحمد لله الذي خلقنا وجعلنا نحن نحن من النسل الحمد لله الذي خلقنا وجعلنا نحن نحن من النسل الحمد لله ا… |
| historyar_0020 | 1400% | ٧٢ | اللهُ لا إلهَ إلاَّ هوُ الحمدُ للهِ |
| historyar_0116 | 1318% | واحده وخمس وعشروں ثانىه ڡىكون صعڡ قوس طه خمسة | الله لا إله إلا هو لا شريك له لا تكفر به ولا تكفر به ولا تكفر به ولا تكفر به ولا تكفر به ولا تكفر به ولا تكفر به ولا تكف… |
| khatt_0056 | 820% | واراق ، غيظ ، ناء ، بث ، نسر . | وارم، حيث (15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 15، 1… |
| historyar_0091 | 400% | صح | الْحَمْدُ لِلَّهِ |
| historyar_0028 | 325% | مسطح | $\frac{1}{2}$ |
| pats_0116 | 322% | بن دينار عن زيد بن أسلم عن عطاء بن يسار عن أبي هريرة أن رسول الله صلى الله عليه وسلم قال | 弟子贤人伊本·阿斯勒从伊本·伊萨尔从阿比·赫里耶人说，真主的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的使者安拉之名，安拉的… |
| historyar_0134 | 233% | لَتِهِ | الْحَمْدُ لله |
| khatt_0189 | 158% | يتكلم وهو نائم بكلمات لا أفهمها مثل انقض بفلس له الضابط لزمتك. سألت راجح هل بلغ | يَعْلَمُونَ وَمَا نَادِمُونَ مِنْكُمْ مِنْهُمْ ۚ ۸۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰۰… |
| historyar_0094 | 150% | لث | الله |
| khatt_0127 | 113% | بيئتنا و ماضينا لكي نساهم في مستقبل و حضارة هذه الأمة حتى تكون مشاركتنا | بَيْتُنا، وَما كُنتُمْ تَكْتُبُونَ، فَإِذَا كَانَتْ مِنْكُمْ مَّا كُنتُمْ تَكْتُبُونَ، فَإِذَا كَانَتْ مِنْكُمْ مَّا كُن… |
| historyar_0169 | 105% | ىساركه فى الطول وڡرى | الله لا إله إلا هو الحمد لله |
| historyar_0183 | 100% | تكونُ مُنتصبَةً | الله |

### Tesseract 5 (ara)

| id | CER | ground truth | prediction |
|---|---:|---|---|
| khatt_0094 | 100% | وفي جملة أسباب ضيق جزيرة العرب عن استيعاب العدد الكبير | *(empty)* |
| historyar_0053 | 100% | ليْس فيها اعْوجَاج | *(empty)* |
| historyar_0004 | 100% | نصف الںهار ڡى كل موصع | *(empty)* |
| historyar_0007 | 100% | الاول من الدّايره الٮى تمر على | *(empty)* |
| pats_0343 | 100% | عمر بن الخطاب جاء يوم الخندق بعد ما غربت الشمس فجعل يسب كفار قريش قال يا رسول الله ما | *(empty)* |
| historyar_0008 | 100% | الاسمين من كل من الثلاثة الاول مشارک لاكبرهما وأنه فى كل من الثلاثه ا[؟ | *(empty)* |
| pats_0332 | 100% | وكن نساء يبعثن إلى عائشة بالدرجة فيها الكرسف فيه الصفرة فتقول لا تعجلن حتى ترين القصة | *(empty)* |
| historyar_0011 | 100% | لل لى حعڡر الخادن | *(empty)* |
| historyar_0017 | 100% | وَالاحْدَی وَالثّلَاثِينَ دَقِيقَةََ وَالخَمْسِ وَالخَمْسِينَ ثَانِيةََ نِسْبَةَ الْمِايةِ وَالإِثْنَی | *(empty)* |
| historyar_0020 | 100% | ٧٢ | 4 |
| historyar_0021 | 100% | وَنَعْنِي بِاجْزآءِ الاوْتارِ الّتِي يَكُونُ الْقُطرُ ١٢٠ جُزْءًا مِنْ تِلْكَ الأَجْزَآءِ | *(empty)* |
| historyar_0022 | 100% | ڡرى الكل على دلک الخط مرٮع | *(empty)* |
| historyar_0023 | 100% | عَشَرَ مِنْ فَلَكِ الْبُرُوج يُسَاوِي زَمَانُ طُلُوعِهِ زَمَانَ طُلوُعِ الْبَاقِي منْ رُبُعِ | *(empty)* |
| historyar_0024 | 100% | هَذِهِ | *(empty)* |
| historyar_0025 | 100% | الحساب | *(empty)* |

### EasyOCR (ar)

| id | CER | ground truth | prediction |
|---|---:|---|---|
| historyar_0087 | 100% | وكان الكل ىسارک المںطٯ المٯروض | 3 |
| historyar_0107 | 100% | فلك | *(empty)* |
| historyar_0053 | 100% | ليْس فيها اعْوجَاج | ?ذ:/ |
| historyar_0183 | 100% | تكونُ مُنتصبَةً | *(empty)* |
| historyar_0091 | 100% | صح | *(empty)* |
| historyar_0094 | 100% | لث | *(empty)* |
| historyar_0011 | 100% | لل لى حعڡر الخادن | ج |
| historyar_0020 | 100% | ٧٢ | *(empty)* |
| historyar_0031 | 100% | صح | *(empty)* |
| historyar_0134 | 100% | لَتِهِ | *(empty)* |
| historyar_0028 | 100% | مسطح | *(empty)* |
| historyar_0025 | 100% | الحساب | *(empty)* |
| historyar_0116 | 98% | واحده وخمس وعشروں ثانىه ڡىكون صعڡ قوس طه خمسة | 3<( 6|<0 |
| historyar_0169 | 95% | ىساركه فى الطول وڡرى | ولسط نسار3 الطول وهر جط وباخه |
| historyar_0129 | 91% | دلک الخط مرٮع خط ىشاركه | الالاخفظ كا ذا لكل ناذفرواد |
