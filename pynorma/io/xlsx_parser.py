import pandas as pd
import openpyxl
from typing import Union, Literal

# 이제 파서는 Trimmer와 Utils의 기능을 가져다 쓰기만 하면 됩니다.
from pynorma.io.trimmer import trim_dataframe
from pynorma.utils import clean_dataframe

def _unmerge_cells(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """
    (엑셀 고유 기능) 워크시트의 모든 병합된 셀을 해제하고 첫 셀의 값으로 채웁니다.
    """
    # 이 함수는 엑셀 파일 처리의 고유한 부분이므로 여기에 남겨둡니다.
    for merged_range in list(ws.merged_cells.ranges):
        min_col, min_row, max_col, max_row = merged_range.bounds
        top_left_cell_value = ws.cell(row=min_row, column=min_col).value
        ws.unmerge_cells(str(merged_range))
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                ws.cell(row=row, column=col).value = top_left_cell_value


def parse_xlsx(
    filepath: str,
    sheet: Union[int, str, None] = None,
    trim: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True
) -> pd.DataFrame:
    """
    (개선된 방식) XLSX 파일을 한 번만 읽고, Trimmer에게 후처리를 위임합니다.

    Args:
        filepath (str): XLSX 파일 경로.
        sheet (int, str, or None), optional): 읽어올 시트 이름 또는 번호. None일 경우 첫 번째 시트를 읽습니다.
        trim (bool, "auto", or dict, optional): 트림 모드. Trimmer에게 그대로 전달됩니다.
        set_header (bool, optional): 헤더 설정 여부. Trimmer에게 그대로 전달됩니다.

    Returns:
        pd.DataFrame: 전처리가 완료된 데이터프레임.
    """
    try:
        # data_only=True는 수식 대신 계산된 값을 가져옵니다.
        wb = openpyxl.load_workbook(filepath, data_only=True)
        
        if sheet is None:
            ws = wb.active
        elif isinstance(sheet, str):
            ws = wb[sheet]
        elif isinstance(sheet, int):
            ws = wb.worksheets[sheet]
        else:
            raise TypeError("The 'sheet' argument must be a string, an integer, or None.")

    except Exception as e:
        print(f"Error opening or finding sheet in Excel file: {e}")
        raise

    # 1. 엑셀의 고유 특성인 '셀 병합'을 먼저 처리합니다.
    _unmerge_cells(ws)

    # 2. 값만 추출하여 raw 데이터프레임을 만듭니다.
    data = ws.values
    df_raw = pd.DataFrame(data)
    
    # 3. 기본적인 클리닝을 수행합니다.
    df_raw = clean_dataframe(df_raw)

    # 4. 똑똑한 Trimmer에게 트림과 헤더 설정을 모두 위임합니다.
    df_clean = trim_dataframe(df_raw, trim_mode=trim, set_header=set_header)
    
    return df_clean