def calculate_bullpen_fatigue_score(workload_ip_last_3d):
    """
    Menghitung skor fatigue bullpen berdasarkan total IP reliever dalam 3 hari terakhir.
    
    Args:
        workload_ip_last_3d (float): Total IP reliever 3 hari terakhir.
        
    Returns:
        tuple: (modifier, reasons)
    """
    try:
        if workload_ip_last_3d is None:
            return 0.0, ["Data workload bullpen tidak tersedia."]
            
        workload = float(workload_ip_last_3d)
        
        if workload > 9.0:
            return 0.4, [f"Bullpen lelah (workload 3 hari terakhir {workload:.1f} IP): +0.40 run"]
        elif workload > 6.0:
            return 0.2, [f"Bullpen agak lelah (workload 3 hari terakhir {workload:.1f} IP): +0.20 run"]
        else:
            return 0.0, []
    except Exception as e:
        # Fungsi ini TIDAK BOLEH raise exception dalam kondisi apa pun
        return 0.0, []
