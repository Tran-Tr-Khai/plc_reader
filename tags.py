DWORD_TAGS = {
    "Counter A",
    "Counter B",
    "Counter Total",
}

# These PLC registers store tenths of their display unit.  Convert them at the
# reader boundary so every API consumer receives the engineering value.
SCALE_DIVISORS = {
    "Tốc độ": 10,
    "Counter A": 10,
    "Counter B": 10,
    "Counter Total": 10,
}


ADDRESS_GROUPS = {
    "speed_and_width": {
        "Tốc độ": "M603",
        "Counter A": "M420",
        "Counter B": "M421",
        "Counter Total": "M422",
        "Bộ đo khổ rộng đầu vào": "M872",
        "Bộ đo khổ rộng giữa #1": "M878",
        "Bộ đo khổ rộng giữa #2": "M880",
        "Bộ đo khổ rộng máy định hình": "M874",
        "Bộ đo khổ rộng đầu ra": "M876",
    },
    "process_PV": {
        "Overfeed (%) – cấp dư vải": "M600",
        "Feed-in (%) – cấp vải vào": "M601",
        "Pinning (%) – ghim biên vải": "M602",
        "Delivery (%) – tốc độ đưa vải ra": "M605",
        "Xi lanh làm mát (%)": "M606",
        "Tỷ lệ kéo vải ra (%)": "M607",
        "Hút/xả khí đầu ra": "M530",
        "Cảm biến độ ẩm khí thải": "M1120",
    },
    "process_SV": {
        "Overfeed (%) – cấp dư vải": "M1600",
        "Feed-in (%) – cấp vải vào": "M1601",
        "Pinning (%) – ghim biên vải": "M1602",
        "Delivery (%) – tốc độ đưa vải ra": "M1605",
        "Xi lanh làm mát (%)": "M1606",
        "Tỷ lệ kéo vải ra (%)": "M1607",
        **{f"Tốc độ hút/xả khí #{i:02d}": f"M{1519 + i}" for i in range(1, 9)},
        "Hút/xả khí đầu ra": "M1530",
        "Cảm biến độ ẩm khí thải": "M1645",
    },
    "chamber_temp_PV": {
        "Chamber #01": "M550",
        "Chamber #02": "M551",
        "Chamber #03": "M552",
        "Chamber #04": "M553",
        "Chamber #05": "M554",
        "Chamber #06": "M555",
        "Chamber #07": "M556",
        "Chamber #08": "M557",
        "Chamber #09": "M558",
        "Chamber #10": "M559",
    },
    # Keep this group name for compatibility with the original script.
    "chamber_tempe_SV": {
        "Chamber #01": "M1550",
        "Chamber #02": "M1551",
        "Chamber #03": "M1552",
        "Chamber #04": "M1553",
        "Chamber #05": "M1554",
        "Chamber #06": "M1555",
        "Chamber #07": "M1556",
        "Chamber #08": "M1557",
        "Chamber #09": "M1558",
        "Chamber #10": "M1559",
    },
}
