/**
 * City and Airport Code Mappings
 * Shared utility for flight search functionality
 */

export interface CityData {
	name: string;
	chinese: string;
	code: string;
	display: string;
}

// City list with display names for autocomplete
export const cityList: CityData[] = [
	// Hong Kong
	{ name: 'Hong Kong', chinese: '香港', code: 'HKG', display: 'Hong Kong (香港) - HKG' },
	
	// Popular Asian Destinations from HKG
	{ name: 'Seoul', chinese: '首爾', code: 'ICN', display: 'Seoul (首爾) - ICN' },
	{ name: 'Busan', chinese: '釜山', code: 'PUS', display: 'Busan (釜山) - PUS' },
	{ name: 'Jeju', chinese: '濟州', code: 'CJU', display: 'Jeju (濟州) - CJU' },
	{ name: 'Tokyo', chinese: '東京', code: 'NRT', display: 'Tokyo (東京) - NRT' },
	{ name: 'Osaka', chinese: '大阪', code: 'KIX', display: 'Osaka (大阪) - KIX' },
	{ name: 'Nagoya', chinese: '名古屋', code: 'NGO', display: 'Nagoya (名古屋) - NGO' },
	{ name: 'Fukuoka', chinese: '福岡', code: 'FUK', display: 'Fukuoka (福岡) - FUK' },
	{ name: 'Sapporo', chinese: '札幌', code: 'CTS', display: 'Sapporo (札幌) - CTS' },
	{ name: 'Okinawa', chinese: '沖繩', code: 'OKA', display: 'Okinawa (沖繩) - OKA' },
	{ name: 'Taipei', chinese: '台北', code: 'TPE', display: 'Taipei (台北) - TPE' },
	{ name: 'Kaohsiung', chinese: '高雄', code: 'KHH', display: 'Kaohsiung (高雄) - KHH' },
	{ name: 'Taichung', chinese: '台中', code: 'RMQ', display: 'Taichung (台中) - RMQ' },
	
	// China Mainland
	{ name: 'Shanghai', chinese: '上海', code: 'PVG', display: 'Shanghai (上海) - PVG' },
	{ name: 'Beijing', chinese: '北京', code: 'PEK', display: 'Beijing (北京) - PEK' },
	{ name: 'Guangzhou', chinese: '廣州', code: 'CAN', display: 'Guangzhou (廣州) - CAN' },
	{ name: 'Shenzhen', chinese: '深圳', code: 'SZX', display: 'Shenzhen (深圳) - SZX' },
	{ name: 'Chengdu', chinese: '成都', code: 'CTU', display: 'Chengdu (成都) - CTU' },
	{ name: 'Xiamen', chinese: '廈門', code: 'XMN', display: 'Xiamen (廈門) - XMN' },
	{ name: 'Hangzhou', chinese: '杭州', code: 'HGH', display: 'Hangzhou (杭州) - HGH' },
	{ name: 'Nanjing', chinese: '南京', code: 'NKG', display: 'Nanjing (南京) - NKG' },
	{ name: 'Qingdao', chinese: '青島', code: 'TAO', display: 'Qingdao (青島) - TAO' },
	{ name: 'Kunming', chinese: '昆明', code: 'KMG', display: 'Kunming (昆明) - KMG' },
	{ name: 'Wuhan', chinese: '武漢', code: 'WUH', display: 'Wuhan (武漢) - WUH' },
	{ name: 'Xian', chinese: '西安', code: 'XIY', display: 'Xian (西安) - XIY' },
	
	// Southeast Asia
	{ name: 'Singapore', chinese: '新加坡', code: 'SIN', display: 'Singapore (新加坡) - SIN' },
	{ name: 'Bangkok', chinese: '曼谷', code: 'BKK', display: 'Bangkok (曼谷) - BKK' },
	{ name: 'Phuket', chinese: '布吉', code: 'HKT', display: 'Phuket (布吉) - HKT' },
	{ name: 'Chiang Mai', chinese: '清邁', code: 'CNX', display: 'Chiang Mai (清邁) - CNX' },
	{ name: 'Pattaya', chinese: '芭堤雅', code: 'UTP', display: 'Pattaya (芭堤雅) - UTP' },
	{ name: 'Krabi', chinese: '喀比', code: 'KBV', display: 'Krabi (喀比) - KBV' },
	{ name: 'Kuala Lumpur', chinese: '吉隆坡', code: 'KUL', display: 'Kuala Lumpur (吉隆坡) - KUL' },
	{ name: 'Penang', chinese: '檳城', code: 'PEN', display: 'Penang (檳城) - PEN' },
	{ name: 'Kota Kinabalu', chinese: '亞庇', code: 'BKI', display: 'Kota Kinabalu (亞庇) - BKI' },
	{ name: 'Langkawi', chinese: '浮羅交怡', code: 'LGK', display: 'Langkawi (浮羅交怡) - LGK' },
	{ name: 'Manila', chinese: '馬尼拉', code: 'MNL', display: 'Manila (馬尼拉) - MNL' },
	{ name: 'Cebu', chinese: '宿霧', code: 'CEB', display: 'Cebu (宿霧) - CEB' },
	{ name: 'Boracay', chinese: '長灘島', code: 'MPH', display: 'Boracay (長灘島) - MPH' },
	{ name: 'Ho Chi Minh', chinese: '胡志明市', code: 'SGN', display: 'Ho Chi Minh (胡志明市) - SGN' },
	{ name: 'Hanoi', chinese: '河內', code: 'HAN', display: 'Hanoi (河內) - HAN' },
	{ name: 'Da Nang', chinese: '峴港', code: 'DAD', display: 'Da Nang (峴港) - DAD' },
	{ name: 'Nha Trang', chinese: '芽莊', code: 'CXR', display: 'Nha Trang (芽莊) - CXR' },
	{ name: 'Jakarta', chinese: '雅加達', code: 'CGK', display: 'Jakarta (雅加達) - CGK' },
	{ name: 'Bali', chinese: '峇里', code: 'DPS', display: 'Bali (峇里) - DPS' },
	{ name: 'Phnom Penh', chinese: '金邊', code: 'PNH', display: 'Phnom Penh (金邊) - PNH' },
	{ name: 'Siem Reap', chinese: '暹粒', code: 'REP', display: 'Siem Reap (暹粒) - REP' },
	
	// Middle East
	{ name: 'Dubai', chinese: '杜拜', code: 'DXB', display: 'Dubai (杜拜) - DXB' },
	{ name: 'Abu Dhabi', chinese: '阿布達比', code: 'AUH', display: 'Abu Dhabi (阿布達比) - AUH' },
	{ name: 'Doha', chinese: '多哈', code: 'DOH', display: 'Doha (多哈) - DOH' },
	
	// Australia & New Zealand
	{ name: 'Sydney', chinese: '雪梨', code: 'SYD', display: 'Sydney (雪梨) - SYD' },
	{ name: 'Melbourne', chinese: '墨爾本', code: 'MEL', display: 'Melbourne (墨爾本) - MEL' },
	{ name: 'Brisbane', chinese: '布里斯本', code: 'BNE', display: 'Brisbane (布里斯本) - BNE' },
	{ name: 'Perth', chinese: '珀斯', code: 'PER', display: 'Perth (珀斯) - PER' },
	{ name: 'Auckland', chinese: '奧克蘭', code: 'AKL', display: 'Auckland (奧克蘭) - AKL' },
	{ name: 'Christchurch', chinese: '基督城', code: 'CHC', display: 'Christchurch (基督城) - CHC' },
	
	// Europe
	{ name: 'London', chinese: '倫敦', code: 'LHR', display: 'London (倫敦) - LHR' },
	{ name: 'Paris', chinese: '巴黎', code: 'PAR', display: 'Paris (巴黎) - PAR' },
	{ name: 'Frankfurt', chinese: '法蘭克福', code: 'FRA', display: 'Frankfurt (法蘭克福) - FRA' },
	{ name: 'Munich', chinese: '慕尼黑', code: 'MUC', display: 'Munich (慕尼黑) - MUC' },
	{ name: 'Amsterdam', chinese: '阿姆斯特丹', code: 'AMS', display: 'Amsterdam (阿姆斯特丹) - AMS' },
	{ name: 'Rome', chinese: '羅馬', code: 'FCO', display: 'Rome (羅馬) - FCO' },
	{ name: 'Madrid', chinese: '馬德里', code: 'MAD', display: 'Madrid (馬德里) - MAD' },
	{ name: 'Barcelona', chinese: '巴塞隆拿', code: 'BCN', display: 'Barcelona (巴塞隆拿) - BCN' },
	{ name: 'Vienna', chinese: '維也納', code: 'VIE', display: 'Vienna (維也納) - VIE' },
	{ name: 'Zurich', chinese: '蘇黎世', code: 'ZRH', display: 'Zurich (蘇黎世) - ZRH' },
	{ name: 'Copenhagen', chinese: '哥本哈根', code: 'CPH', display: 'Copenhagen (哥本哈根) - CPH' },
	{ name: 'Stockholm', chinese: '斯德哥爾摩', code: 'ARN', display: 'Stockholm (斯德哥爾摩) - ARN' },
	{ name: 'Oslo', chinese: '奧斯陸', code: 'OSL', display: 'Oslo (奧斯陸) - OSL' },
	{ name: 'Helsinki', chinese: '赫爾辛基', code: 'HEL', display: 'Helsinki (赫爾辛基) - HEL' },
	{ name: 'Istanbul', chinese: '伊斯坦堡', code: 'IST', display: 'Istanbul (伊斯坦堡) - IST' },
	
	// North America
	{ name: 'New York', chinese: '紐約', code: 'JFK', display: 'New York (紐約) - JFK' },
	{ name: 'Los Angeles', chinese: '洛杉磯', code: 'LAX', display: 'Los Angeles (洛杉磯) - LAX' },
	{ name: 'San Francisco', chinese: '三藩市', code: 'SFO', display: 'San Francisco (三藩市) - SFO' },
	{ name: 'Vancouver', chinese: '溫哥華', code: 'YVR', display: 'Vancouver (溫哥華) - YVR' },
	{ name: 'Toronto', chinese: '多倫多', code: 'YYZ', display: 'Toronto (多倫多) - YYZ' },
	{ name: 'Chicago', chinese: '芝加哥', code: 'ORD', display: 'Chicago (芝加哥) - ORD' },
	{ name: 'Seattle', chinese: '西雅圖', code: 'SEA', display: 'Seattle (西雅圖) - SEA' },
	
	// South Asia & India
	{ name: 'Delhi', chinese: '德里', code: 'DEL', display: 'Delhi (德里) - DEL' },
	{ name: 'Mumbai', chinese: '孟買', code: 'BOM', display: 'Mumbai (孟買) - BOM' },
	{ name: 'Bangalore', chinese: '班加羅爾', code: 'BLR', display: 'Bangalore (班加羅爾) - BLR' },
	{ name: 'Colombo', chinese: '可倫坡', code: 'CMB', display: 'Colombo (可倫坡) - CMB' },
	{ name: 'Male', chinese: '馬爾代夫', code: 'MLE', display: 'Male (馬爾代夫) - MLE' },
	
	// Africa
	{ name: 'Cairo', chinese: '開羅', code: 'CAI', display: 'Cairo (開羅) - CAI' },
	{ name: 'Johannesburg', chinese: '約翰尼斯堡', code: 'JNB', display: 'Johannesburg (約翰尼斯堡) - JNB' },
	{ name: 'Cape Town', chinese: '開普敦', code: 'CPT', display: 'Cape Town (開普敦) - CPT' }
];

// Location code mapping for common cities (key: city name or code -> value: IATA code)
export const locationCodeMap: Record<string, string> = {
	// Direct airport code mappings (most important - these should be checked first)
	'HKG': 'HKG',
	'ICN': 'ICN',
	'PUS': 'PUS',
	'CJU': 'CJU',
	'NRT': 'NRT',
	'KIX': 'KIX',
	'TPE': 'TPE',
	'KHH': 'KHH',
	'RMQ': 'RMQ',
	'SIN': 'SIN',
	'BKK': 'BKK',
	'HKT': 'HKT',
	'CNX': 'CNX',
	'UTP': 'UTP',
	'KBV': 'KBV',
	'KUL': 'KUL',
	'PEN': 'PEN',
	'BKI': 'BKI',
	'LGK': 'LGK',
	'MNL': 'MNL',
	'CEB': 'CEB',
	'MPH': 'MPH',
	'SGN': 'SGN',
	'HAN': 'HAN',
	'DAD': 'DAD',
	'CXR': 'CXR',
	'CGK': 'CGK',
	'DPS': 'DPS',
	'PNH': 'PNH',
	'REP': 'REP',
	'DXB': 'DXB',
	'AUH': 'AUH',
	'DOH': 'DOH',
	'LHR': 'LHR',
	'JFK': 'JFK',
	'LAX': 'LAX',
	'SFO': 'SFO',
	'ORD': 'ORD',
	'SEA': 'SEA',
	'SYD': 'SYD',
	'AKL': 'AKL',
	'CHC': 'CHC',
	'CDG': 'PAR', // Paris Charles de Gaulle
	'FRA': 'FRA',
	'MUC': 'MUC',
	'AMS': 'AMS',
	'FCO': 'FCO',
	'ZRH': 'ZRH',
	'YVR': 'YVR',
	'YYZ': 'YYZ',
	'NGO': 'NGO',
	'FUK': 'FUK',
	'CTS': 'CTS',
	'OKA': 'OKA',
	'DEL': 'DEL',
	'BOM': 'BOM',
	'BLR': 'BLR',
	'CMB': 'CMB',
	'MLE': 'MLE',
	'PEK': 'PEK',
	'PVG': 'PVG',
	'CAN': 'CAN',
	'SZX': 'SZX',
	'CTU': 'CTU',
	'XIY': 'XIY',
	'NKG': 'NKG',
	'TAO': 'TAO',
	'TSN': 'TSN',
	'CKG': 'CKG',
	'URC': 'URC',
	'HRB': 'HRB',
	'DLC': 'DLC',
	'SJW': 'SJW',
	'TYN': 'TYN',
	'INC': 'INC',
	'LHW': 'LHW',
	'XNN': 'XNN',
	'KMG': 'KMG',
	'LXA': 'LXA',
	'HAK': 'HAK',
	'FOC': 'FOC',
	'XMN': 'XMN',
	'CSX': 'CSX',
	'WUH': 'WUH',
	'CGO': 'CGO',
	'JIN': 'JIN',
	'YNT': 'YNT',
	'WEH': 'WEH',
	'LYG': 'LYG',
	'NTG': 'NTG',
	'WNZ': 'WNZ',
	'NGB': 'NGB',
	'HGH': 'HGH',
	'MEL': 'MEL',
	'BNE': 'BNE',
	'PER': 'PER',
	'ADL': 'ADL',
	'CBR': 'CBR',
	'HOB': 'HOB',
	'DRW': 'DRW',
	'CNS': 'CNS',
	'TSV': 'TSV',
	'OOL': 'OOL',
	'MCY': 'MCY',
	'ROK': 'ROK',
	'MAD': 'MAD',
	'BCN': 'BCN',
	'ZUR': 'ZUR',
	'VIE': 'VIE',
	'CPH': 'CPH',
	'ARN': 'ARN',
	'OSL': 'OSL',
	'HEL': 'HEL',
	'WAW': 'WAW',
	'PRG': 'PRG',
	'BUD': 'BUD',
	'ATH': 'ATH',
	'IST': 'IST',
	'KWI': 'KWI',
	'BAH': 'BAH',
	'JED': 'JED',
	'RUH': 'RUH',
	'CAI': 'CAI',
	'JNB': 'JNB',
	'CPT': 'CPT',
	'LOS': 'LOS',
	'NBO': 'NBO',
	'ADD': 'ADD',
	'KRT': 'KRT',
	'KGL': 'KGL',
	'DAR': 'DAR',
	'LUN': 'LUN',
	'GBE': 'GBE',
	'WDH': 'WDH',
	'MPM': 'MPM',
	'BJM': 'BJM',
	
	// City name mappings (lowercase for case-insensitive lookup)
	'香港': 'HKG',
	'hong kong': 'HKG',
	
	// Korea
	'首爾': 'ICN',
	'seoul': 'ICN',
	'釜山': 'PUS',
	'busan': 'PUS',
	'濟州': 'CJU',
	'jeju': 'CJU',
	
	// Taiwan
	'台北': 'TPE',
	'taipei': 'TPE',
	'高雄': 'KHH',
	'kaohsiung': 'KHH',
	'台中': 'RMQ',
	'taichung': 'RMQ',
	
	// Japan
	'東京': 'NRT',
	'tokyo': 'NRT',
	'大阪': 'KIX',
	'osaka': 'KIX',
	'名古屋': 'NGO',
	'nagoya': 'NGO',
	'福岡': 'FUK',
	'fukuoka': 'FUK',
	'札幌': 'CTS',
	'sapporo': 'CTS',
	'沖繩': 'OKA',
	'okinawa': 'OKA',
	'japan': 'NRT',
	'japanese': 'NRT',
	
	// China Mainland
	'上海': 'PVG',
	'shanghai': 'PVG',
	'北京': 'PEK',
	'beijing': 'PEK',
	'廣州': 'CAN',
	'guangzhou': 'CAN',
	'深圳': 'SZX',
	'shenzhen': 'SZX',
	'成都': 'CTU',
	'chengdu': 'CTU',
	'廈門': 'XMN',
	'xiamen': 'XMN',
	'杭州': 'HGH',
	'hangzhou': 'HGH',
	'南京': 'NKG',
	'nanjing': 'NKG',
	'青島': 'TAO',
	'qingdao': 'TAO',
	'昆明': 'KMG',
	'kunming': 'KMG',
	'武漢': 'WUH',
	'wuhan': 'WUH',
	'西安': 'XIY',
	'xian': 'XIY',
	
	// Singapore
	'新加坡': 'SIN',
	'singapore': 'SIN',
	
	// Thailand
	'曼谷': 'BKK',
	'bangkok': 'BKK',
	'布吉': 'HKT',
	'phuket': 'HKT',
	'清邁': 'CNX',
	'chiang mai': 'CNX',
	'芭堤雅': 'UTP',
	'pattaya': 'UTP',
	'喀比': 'KBV',
	'krabi': 'KBV',
	
	// Malaysia
	'吉隆坡': 'KUL',
	'kuala lumpur': 'KUL',
	'檳城': 'PEN',
	'penang': 'PEN',
	'亞庇': 'BKI',
	'kota kinabalu': 'BKI',
	'浮羅交怡': 'LGK',
	'langkawi': 'LGK',
	
	// Philippines
	'馬尼拉': 'MNL',
	'manila': 'MNL',
	'宿霧': 'CEB',
	'cebu': 'CEB',
	'長灘島': 'MPH',
	'boracay': 'MPH',
	
	// Vietnam
	'胡志明市': 'SGN',
	'ho chi minh': 'SGN',
	'河內': 'HAN',
	'hanoi': 'HAN',
	'峴港': 'DAD',
	'da nang': 'DAD',
	'芽莊': 'CXR',
	'nha trang': 'CXR',
	
	// Indonesia
	'雅加達': 'CGK',
	'jakarta': 'CGK',
	'峇里': 'DPS',
	'bali': 'DPS',
	
	// Cambodia
	'金邊': 'PNH',
	'phnom penh': 'PNH',
	'暹粒': 'REP',
	'siem reap': 'REP',
	
	// Middle East
	'杜拜': 'DXB',
	'dubai': 'DXB',
	'阿布達比': 'AUH',
	'abu dhabi': 'AUH',
	'多哈': 'DOH',
	'doha': 'DOH',
	
	// Australia & New Zealand
	'雪梨': 'SYD',
	'sydney': 'SYD',
	'墨爾本': 'MEL',
	'melbourne': 'MEL',
	'布里斯本': 'BNE',
	'brisbane': 'BNE',
	'珀斯': 'PER',
	'perth': 'PER',
	'奧克蘭': 'AKL',
	'auckland': 'AKL',
	'基督城': 'CHC',
	'christchurch': 'CHC',
	
	// Europe
	'倫敦': 'LHR',
	'london': 'LHR',
	'巴黎': 'PAR',
	'paris': 'PAR',
	'法蘭克福': 'FRA',
	'frankfurt': 'FRA',
	'慕尼黑': 'MUC',
	'munich': 'MUC',
	'阿姆斯特丹': 'AMS',
	'amsterdam': 'AMS',
	'羅馬': 'FCO',
	'rome': 'FCO',
	'馬德里': 'MAD',
	'madrid': 'MAD',
	'巴塞隆拿': 'BCN',
	'barcelona': 'BCN',
	'維也納': 'VIE',
	'vienna': 'VIE',
	'蘇黎世': 'ZRH',
	'zurich': 'ZRH',
	'哥本哈根': 'CPH',
	'copenhagen': 'CPH',
	'斯德哥爾摩': 'ARN',
	'stockholm': 'ARN',
	'奧斯陸': 'OSL',
	'oslo': 'OSL',
	'赫爾辛基': 'HEL',
	'helsinki': 'HEL',
	'伊斯坦堡': 'IST',
	'istanbul': 'IST',
	
	// North America
	'紐約': 'JFK',
	'new york': 'JFK',
	'洛杉磯': 'LAX',
	'los angeles': 'LAX',
	'三藩市': 'SFO',
	'san francisco': 'SFO',
	'溫哥華': 'YVR',
	'vancouver': 'YVR',
	'多倫多': 'YYZ',
	'toronto': 'YYZ',
	'芝加哥': 'ORD',
	'chicago': 'ORD',
	'西雅圖': 'SEA',
	'seattle': 'SEA',
	
	// South Asia & India
	'德里': 'DEL',
	'delhi': 'DEL',
	'孟買': 'BOM',
	'mumbai': 'BOM',
	'班加羅爾': 'BLR',
	'bangalore': 'BLR',
	'可倫坡': 'CMB',
	'colombo': 'CMB',
	'馬爾代夫': 'MLE',
	'male': 'MLE',
	'maldives': 'MLE',
	
	// Africa
	'開羅': 'CAI',
	'cairo': 'CAI',
	'約翰尼斯堡': 'JNB',
	'johannesburg': 'JNB',
	'開普敦': 'CPT',
	'cape town': 'CPT'
};

/**
 * Get location code from city name or airport code
 * @param cityName - City name (English/Chinese) or IATA code
 * @returns IATA airport code or null if not found
 */
export const getLocationCode = (cityName: string): string | null => {
	if (!cityName) return null;
	
	// Clean the input - remove extra spaces and convert to uppercase for airport codes
	const cleanName = cityName.trim();
	
	// First try exact match (case insensitive for city names, case sensitive for airport codes)
	const exactMatch = locationCodeMap[cleanName.toLowerCase()] || locationCodeMap[cleanName.toUpperCase()];
	if (exactMatch) return exactMatch;
	
	// Try partial match for city names (case insensitive)
	for (const [key, code] of Object.entries(locationCodeMap)) {
		if (key.toLowerCase().includes(cleanName.toLowerCase()) || cleanName.toLowerCase().includes(key.toLowerCase())) {
			return code;
		}
	}
	
	// If no match found, return null to indicate invalid input
	return null;
};

/**
 * Filter cities based on search input
 * @param input - Search term
 * @returns Filtered city list
 */
export const filterCities = (input: string): CityData[] => {
	if (!input || input.trim() === '') {
		return cityList.slice(0, 10); // Show top 10 cities when empty
	}
	
	const searchTerm = input.toLowerCase().trim();
	return cityList.filter(city => 
		city.name.toLowerCase().includes(searchTerm) ||
		city.chinese.includes(searchTerm) ||
		city.code.toLowerCase().includes(searchTerm) ||
		city.display.toLowerCase().includes(searchTerm)
	);
};

