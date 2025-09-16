import openpyxl

def export_report_to_excel(report, filename="report.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders Report"
    
    # Header
    ws.append(["Item", "Quantity", "Total Price"])
    
    # Rows
    for name, total, total_price in report:
        ws.append([name, total, total_price])
    
    # Save
    wb.save(filename)
    return filename
