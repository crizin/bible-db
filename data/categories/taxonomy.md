# 성경 어휘 의미 카테고리 (Semantic Domains)

각 Strong 엔트리(원어 단어)를 아래 체계로 분류한다. **multi-label** 허용 — 한 단어가 여러 카테고리에 속할 수 있다(예: "어린 양" = 동물>가축 + 종교의례>제물). 명사·구체 개념은 소분류까지 정확히, 추상·행위·기능어도 빠짐없이 분류한다.

형식: `major>minor` (예: `animal>livestock`). 영문 키를 쓴다.

## 대분류 > 소분류

1. **animal** (동물): livestock(가축) · wild_animal(야생) · bird(새) · fish_aquatic(어패류) · insect(곤충) · reptile(파충양서) · animal_product(가죽/뿔/털 등 산물)
2. **plant** (식물): tree(나무) · fruit(과일) · grain(곡물) · vegetable(채소콩) · vine_wine(포도/포도주) · herb_grass(풀꽃) · spice_incense(향료향) · plant_part(가지/뿌리 등)
3. **human_body** (인체): body_part(부위) · body_fluid(체액) · health_disease(건강질병)
4. **person_role** (사람·역할): kinship(친족) · occupation(직업) · rank_status(지위) · people_group(민족집단) · personal_name(인명)
5. **deity_spirit** (신·영): divine_name(신호칭) · angel(천사) · demon_idol(악령우상)
6. **place** (장소): place_name(지명) · landform(지형) · building(건물) · settlement(도시정착) · spatial_direction(공간방향)
7. **nature** (자연): celestial(천체) · weather(기상) · water(물) · fire_light(불빛) · mineral_gem(광물보석) · metal(금속) · earth_stone(흙돌)
8. **artifact** (인공물): weapon(무기) · vessel(그릇) · clothing_ornament(의복장신구) · instrument(악기) · furniture(가구) · tool(도구농기구) · vehicle(운송) · fabric_cord(직물끈)
9. **food_drink** (음식): food(음식) · drink(음료) · seasoning(조미)
10. **time** (시간): time_unit(시간단위) · festival(절기) · period(시기국면)
11. **quantity** (수량): measure(도량형) · number(숫자) · currency_weight(화폐무게)
12. **action** (행위): motion(이동) · speech(말하기) · perception(감각) · make_labor(제작노동) · destroy_violence(파괴폭력) · give_take(주고받음) · physical_act(신체동작)
13. **emotion_mind** (감정심리): emotion(감정) · thought_will(사고의지) · attitude_character(태도성품)
14. **morality_spirituality** (도덕영성): sin_evil(죄악) · righteousness_holiness(의거룩) · law_command(율법계명) · faith_worship(믿음예배) · salvation_covenant(구원언약)
15. **ritual** (종교의례): sacrifice_offering(제사제물) · tabernacle_temple(성막성전) · priesthood(제사장) · purity_rite(정결의식)
16. **society_politics** (사회정치): kingship_rule(왕권) · war_military(전쟁) · law_justice(법재판) · commerce(상업) · slavery(노예)
17. **abstract_quality** (추상속성): quality(성질) · truth_wisdom(진리지혜) · glory_power(영광권능) · state_condition(상태) · color(색)
18. **function_word** (기능어): preposition(전치사) · conjunction(접속사) · pronoun(대명사) · particle_adverb(불변화사부사) · interrogative(의문)

## 분류 규칙

- 각 단어에 **최소 1개, 최대 3개** 카테고리. `primary`는 가장 핵심적인 것 1개.
- 구체 명사 → 소분류까지(`animal>livestock`). 추상/동사 → 대분류 중심이되 가능하면 소분류.
- 기능어(전치사·접속사·대명사·불변화사)는 `function_word>...`로.
- 동음이의/다의어는 주된 의미를 primary로, 부가 의미를 추가 카테고리로.
- 고유명사(인명·지명)는 `person_role>personal_name` / `place>place_name`.
- 정의가 모호하면 가장 가까운 대분류만 부여하고 minor는 생략 가능(`abstract_quality`).
