"""66권 표준 매핑 + 공통 정제 유틸.

(book_num, usfm_code, name_kr, num_chapters) — 표준 프로테스탄트 정경 순서.
holybible VL 파라미터(1~66)와 bskorea KRV.{code} 모두 이 순서/코드를 따른다.
"""
import re

BOOKS = [
    (1, "GEN", "창세기", 50), (2, "EXO", "출애굽기", 40), (3, "LEV", "레위기", 27),
    (4, "NUM", "민수기", 36), (5, "DEU", "신명기", 34), (6, "JOS", "여호수아", 24),
    (7, "JDG", "사사기", 21), (8, "RUT", "룻기", 4), (9, "1SA", "사무엘상", 31),
    (10, "2SA", "사무엘하", 24), (11, "1KI", "열왕기상", 22), (12, "2KI", "열왕기하", 25),
    (13, "1CH", "역대상", 29), (14, "2CH", "역대하", 36), (15, "EZR", "에스라", 10),
    (16, "NEH", "느헤미야", 13), (17, "EST", "에스더", 10), (18, "JOB", "욥기", 42),
    (19, "PSA", "시편", 150), (20, "PRO", "잠언", 31), (21, "ECC", "전도서", 12),
    (22, "SNG", "아가", 8), (23, "ISA", "이사야", 66), (24, "JER", "예레미야", 52),
    (25, "LAM", "예레미야애가", 5), (26, "EZK", "에스겔", 48), (27, "DAN", "다니엘", 12),
    (28, "HOS", "호세아", 14), (29, "JOL", "요엘", 3), (30, "AMO", "아모스", 9),
    (31, "OBA", "오바댜", 1), (32, "JON", "요나", 4), (33, "MIC", "미가", 7),
    (34, "NAM", "나훔", 3), (35, "HAB", "하박국", 3), (36, "ZEP", "스바냐", 3),
    (37, "HAG", "학개", 2), (38, "ZEC", "스가랴", 14), (39, "MAL", "말라기", 4),
    (40, "MAT", "마태복음", 28), (41, "MRK", "마가복음", 16), (42, "LUK", "누가복음", 24),
    (43, "JHN", "요한복음", 21), (44, "ACT", "사도행전", 28), (45, "ROM", "로마서", 16),
    (46, "1CO", "고린도전서", 16), (47, "2CO", "고린도후서", 13), (48, "GAL", "갈라디아서", 6),
    (49, "EPH", "에베소서", 6), (50, "PHP", "빌립보서", 4), (51, "COL", "골로새서", 4),
    (52, "1TH", "데살로니가전서", 5), (53, "2TH", "데살로니가후서", 3), (54, "1TI", "디모데전서", 6),
    (55, "2TI", "디모데후서", 4), (56, "TIT", "디도서", 3), (57, "PHM", "빌레몬서", 1),
    (58, "HEB", "히브리서", 13), (59, "JAS", "야고보서", 5), (60, "1PE", "베드로전서", 5),
    (61, "2PE", "베드로후서", 3), (62, "1JN", "요한일서", 5), (63, "2JN", "요한이서", 1),
    (64, "3JN", "요한삼서", 1), (65, "JUD", "유다서", 1), (66, "REV", "요한계시록", 22),
]

assert sum(b[3] for b in BOOKS) == 1189, "장 수 합계는 1189여야 함"

NAME_BY_CODE = {code: name for _, code, name, _ in BOOKS}
NUM_BY_CODE = {code: num for num, code, _, _ in BOOKS}

# OSIS book code (morphhb WLC 파일/osisID, 일부 원어 소스) → USFM code
OSIS_TO_USFM = {
    "Gen": "GEN", "Exod": "EXO", "Lev": "LEV", "Num": "NUM", "Deut": "DEU",
    "Josh": "JOS", "Judg": "JDG", "Ruth": "RUT", "1Sam": "1SA", "2Sam": "2SA",
    "1Kgs": "1KI", "2Kgs": "2KI", "1Chr": "1CH", "2Chr": "2CH", "Ezra": "EZR",
    "Neh": "NEH", "Esth": "EST", "Job": "JOB", "Ps": "PSA", "Prov": "PRO",
    "Eccl": "ECC", "Song": "SNG", "Isa": "ISA", "Jer": "JER", "Lam": "LAM",
    "Ezek": "EZK", "Dan": "DAN", "Hos": "HOS", "Joel": "JOL", "Amos": "AMO",
    "Obad": "OBA", "Jonah": "JON", "Mic": "MIC", "Nah": "NAM", "Hab": "HAB",
    "Zeph": "ZEP", "Hag": "HAG", "Zech": "ZEC", "Mal": "MAL",
    "Matt": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN", "Acts": "ACT",
    "Rom": "ROM", "1Cor": "1CO", "2Cor": "2CO", "Gal": "GAL", "Eph": "EPH",
    "Phil": "PHP", "Col": "COL", "1Thess": "1TH", "2Thess": "2TH", "1Tim": "1TI",
    "2Tim": "2TI", "Titus": "TIT", "Phlm": "PHM", "Heb": "HEB", "Jas": "JAS",
    "1Pet": "1PE", "2Pet": "2PE", "1John": "1JN", "2John": "2JN", "3John": "3JN",
    "Jude": "JUD", "Rev": "REV",
}


def clean(node):
    """BeautifulSoup 노드 → 순수 본문 텍스트. 태그 제거 + 공백 정규화.
    separator="" 라서 <a>태초</a>에 같은 단어+조사 경계가 안 벌어진다."""
    return re.sub(r"\s+", " ", node.get_text("")).strip()
