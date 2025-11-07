export type AirlineOption = {
  code: string;
  name: string;
};

export const airlineOptions: AirlineOption[] = [
  // Hong Kong & Greater China
  { code: 'HB', name: '大灣區航空' },
  { code: 'CX', name: '國泰航空' },
  { code: 'HX', name: '香港航空' },
  { code: 'UO', name: '香港快運' },

  // Mainland China & Taiwan
  { code: 'CA', name: '中國國際航空' },
  { code: 'MU', name: '中國東方航空' },
  { code: 'CZ', name: '中國南方航空' },
  { code: 'CI', name: '中華航空' },
  { code: 'BR', name: '長榮航空' },
  { code: 'FM', name: '上海航空' },
  { code: 'SC', name: '山東航空' },
  { code: '3U', name: '四川航空' },
  { code: 'MF', name: '廈門航空' },
  { code: 'HU', name: '海南航空' },
  { code: 'HO', name: '吉祥航空' },
  { code: '9C', name: '春秋航空' },
  { code: 'AE', name: '華夏航空' },

  // Other Asian Airlines
  { code: 'AK', name: '亞洲航空' },
  { code: 'FD', name: '泰國亞洲航空' },
  { code: 'Z2', name: '菲律賓亞洲航空' },
  { code: 'MH', name: '馬來西亞航空' },
  { code: 'OD', name: '巴迪航空' },
  { code: 'GA', name: '印尼鷹航' },
  { code: 'AI', name: '印度航空' },
  { code: '6E', name: '靛藍航空' },
  { code: 'JL', name: '日本航空' },
  { code: 'NH', name: '全日空' },
  { code: 'OZ', name: '韓亞航空' },
  { code: 'KE', name: '大韓航空' },
  { code: 'LJ', name: '真航空' },
  { code: '7C', name: '濟州航空' },
  { code: 'ZE', name: '東海航空' },
  { code: 'BX', name: '釜山航空' },
  { code: 'RS', name: '首爾航空' },
  { code: 'SQ', name: '新加坡航空' },
  { code: 'TR', name: '酷航' },
  { code: 'TG', name: '泰國航空' },
  { code: 'PG', name: '曼谷航空' },
  { code: 'VN', name: '越南航空' },
  { code: 'VJ', name: '越捷航空' },
  { code: 'BI', name: '皇家汶萊航空' },
  { code: 'PR', name: '菲律賓航空' },
  { code: '5J', name: '宿霧太平洋航空' },
  { code: 'EK', name: '阿聯酋航空' },
  { code: 'EY', name: '阿提哈德航空' },
  { code: 'QR', name: '卡達航空' },
  { code: 'TK', name: '土耳其航空' },

  // Europe & Russia
  { code: 'SU', name: '俄羅斯航空' },
  { code: 'AF', name: '法國航空' },
  { code: 'KL', name: '荷蘭皇家航空' },
  { code: 'BA', name: '英國航空' },
  { code: 'AY', name: '芬蘭航空' },
  { code: 'LX', name: '瑞士國際航空' },
  { code: 'VS', name: '維珍航空' },
  { code: 'LH', name: '漢莎航空' },

  // North America & Oceania
  { code: 'AC', name: '加拿大航空' },
  { code: 'AA', name: '美國航空' },
  { code: 'UA', name: '聯合航空' },
  { code: 'DL', name: '達美航空' },
  { code: 'NZ', name: '紐西蘭航空' },
  { code: 'QF', name: '澳洲航空' },
  { code: 'FJ', name: '斐濟航空' },

  // Other Regions
  { code: 'LY', name: '以色列航空' },
  { code: 'MS', name: '埃及航空' },
  { code: 'ET', name: '衣索比亞航空' },
  { code: 'MK', name: '毛里求斯航空' },
  { code: 'SA', name: '南非航空' },
  { code: 'RJ', name: '皇家約旦航空' }
];

export const airlineOptionsMap = new Map(airlineOptions.map((airline) => [airline.code, airline]));

