/**
 * Amadeus Flight Offers Search API Service
 * Handles authentication and flight search requests
 */

import { getAmadeusConfig, getDevConfig, isConfigAvailable } from '$lib/config/amadeus.js';

class AmadeusApiService {
	constructor() {
		this.accessToken = null;
		this.tokenExpiry = null;
		this.config = null;
		this.initializeConfig();
	}

	/**
	 * Initialize configuration
	 */
	initializeConfig() {
		try {
			// Try to get production config first
			this.config = getAmadeusConfig();
		} catch (error) {
			// Fall back to development config with warnings
			console.warn('Using development configuration for Amadeus API:', error.message);
			this.config = getDevConfig();
		}
	}

	/**
	 * Get access token from Amadeus API
	 */
	async getAccessToken() {
		// Check if we have a valid token
		if (this.accessToken && this.tokenExpiry && Date.now() < this.tokenExpiry) {
			return this.accessToken;
		}

		try {
			const response = await fetch(`${this.config.BASE_URL}/v1/security/oauth2/token`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded',
				},
				body: new URLSearchParams({
					grant_type: 'client_credentials',
					client_id: this.config.API_KEY,
					client_secret: this.config.API_SECRET,
				}),
			});

			if (!response.ok) {
				throw new Error(`Authentication failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			this.accessToken = data.access_token;
			// Set expiry time (subtract buffer time for safety)
			this.tokenExpiry = Date.now() + (data.expires_in - this.config.TOKEN_EXPIRY_BUFFER) * 1000;

			return this.accessToken;
		} catch (error) {
			console.error('Error getting Amadeus access token:', error);
			throw new Error('Failed to authenticate with Amadeus API');
		}
	}

	/**
	 * Search for flight offers
	 * @param {Object} searchParams - Search parameters
	 * @param {string} searchParams.originLocationCode - Origin airport/city code
	 * @param {string} searchParams.destinationLocationCode - Destination airport/city code
	 * @param {string} searchParams.departureDate - Departure date (YYYY-MM-DD)
	 * @param {string} searchParams.returnDate - Return date (YYYY-MM-DD, optional)
	 * @param {number} searchParams.adults - Number of adult passengers
	 * @param {string} searchParams.travelClass - Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
	 * @param {number} searchParams.max - Maximum number of results
	 */
	async searchFlightOffers(searchParams) {
		try {
			const token = await this.getAccessToken();

			// Build query parameters
			const queryParams = new URLSearchParams({
				originLocationCode: searchParams.originLocationCode,
				destinationLocationCode: searchParams.destinationLocationCode,
				departureDate: searchParams.departureDate,
				adults: searchParams.adults || this.config.DEFAULT_ADULTS,
				travelClass: searchParams.travelClass || this.config.DEFAULT_TRAVEL_CLASS,
				max: searchParams.max || this.config.DEFAULT_MAX_RESULTS,
			});

			// Add return date if provided
			if (searchParams.returnDate) {
				queryParams.append('returnDate', searchParams.returnDate);
			}

			const response = await fetch(`${this.config.BASE_URL}/v2/shopping/flight-offers?${queryParams}`, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(`Flight search failed: ${response.status} ${response.statusText}. ${errorData.detail || ''}`);
			}

			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Error searching flights:', error);
			throw error;
		}
	}

	/**
	 * Get airport/city suggestions for location search
	 * @param {string} keyword - Search keyword
	 * @param {string} subType - Type of location (AIRPORT, CITY, ANY)
	 */
	async getLocationSuggestions(keyword, subType = 'ANY') {
		try {
			const token = await this.getAccessToken();

			const queryParams = new URLSearchParams({
				keyword: keyword,
				subType: subType,
			});

			const response = await fetch(`${this.config.BASE_URL}/v1/reference-data/locations?${queryParams}`, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
			});

			if (!response.ok) {
				throw new Error(`Location search failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Error getting location suggestions:', error);
			throw error;
		}
	}

	/**
	 * Transform Amadeus flight offer data to match our UI structure
	 * @param {Object} amadeusData - Raw data from Amadeus API
	 */
	transformFlightData(amadeusData) {
		if (!amadeusData.data || !Array.isArray(amadeusData.data)) {
			return [];
		}

		return amadeusData.data.map((offer, index) => {
			const itinerary = offer.itineraries[0];
			const segments = itinerary.segments;
			const firstSegment = segments[0];
			const lastSegment = segments[segments.length - 1];

			// Get airline information
			const airlineCode = firstSegment.carrierCode;
			const airlineName = this.getAirlineName(airlineCode);

			// Calculate total price
			const totalPrice = parseFloat(offer.price.total);

			// Get travel class
			const travelClass = this.mapTravelClass(offer.travelerPricings[0].fareOption);

			return {
				id: `amadeus_${index}`,
				airline: airlineName,
				airlineCode: airlineCode,
				startingPlace: this.getCityName(firstSegment.departure.iataCode),
				startingPlaceCode: firstSegment.departure.iataCode,
				destination: this.getCityName(lastSegment.arrival.iataCode),
				destinationCode: lastSegment.arrival.iataCode,
				cost: totalPrice,
				currency: offer.price.currency,
				seatClass: travelClass,
				departureDate: firstSegment.departure.at.split('T')[0],
				departureTime: firstSegment.departure.at.split('T')[1].substring(0, 5),
				arrivalDate: lastSegment.arrival.at.split('T')[0],
				arrivalTime: lastSegment.arrival.at.split('T')[1].substring(0, 5),
				ticketValidDate: lastSegment.arrival.at.split('T')[0],
				duration: this.formatDuration(itinerary.duration),
				segments: segments.length,
				// Store original Amadeus data for reference
				amadeusData: offer
			};
		});
	}

	/**
	 * Map Amadeus travel class to our UI format
	 */
	mapTravelClass(fareOption) {
		const classMap = {
			'STANDARD': 'Economy',
			'INCLUSIVE': 'Economy',
			'BUSINESS': 'Business',
			'FIRST': 'First'
		};
		return classMap[fareOption] || 'Economy';
	}

	/**
	 * Get airline name from IATA code
	 */
	getAirlineName(iataCode) {
		const airlineMap = {
			'CX': '國泰航空',
			'BR': '長榮航空',
			'NH': '全日空航空公司',
			'EK': '阿聯酋航空',
			'BA': '英國航空公司',
			'AA': 'American Airlines',
			'DL': 'Delta Air Lines',
			'UA': 'United Airlines',
			'LH': 'Lufthansa',
			'AF': 'Air France',
			'KL': 'KLM Royal Dutch Airlines',
			'SQ': 'Singapore Airlines',
			'JL': 'Japan Airlines',
			'KE': 'Korean Air',
			'TG': 'Thai Airways',
			'QF': 'Qantas',
			'AC': 'Air Canada',
			'WS': 'WestJet',
			'CZ': '中國南方航空',
			'CA': '中國國際航空',
			'MF': '廈門航空',
			'3U': '四川航空',
			'9C': '春秋航空',
			'HO': '吉祥航空',
			'JD': '首都航空',
			'GS': '天津航空',
			'PN': '西部航空',
			'8L': '祥鵬航空',
			'G5': '華夏航空',
			'KY': '昆明航空',
			'TV': '西藏航空',
			'UQ': '烏魯木齊航空',
			'9H': '長安航空',
			'DR': '瑞麗航空',
			'GJ': '長龍航空',
			'NS': '河北航空',
			'EU': '成都航空',
			'BK': '奧凱航空',
			'FU': '福州航空',
			'GT': '桂林航空',
			'LT': '龍江航空',
			'RY': '江西航空',
			'QW': '青島航空',
			'SC': '山東航空',
			'ZH': '深圳航空',
			'3U': '四川航空',
			'FM': '上海航空',
			'KN': '聯合航空',
			'PN': '西部航空',
			'8L': '祥鵬航空',
			'G5': '華夏航空',
			'KY': '昆明航空',
			'TV': '西藏航空',
			'UQ': '烏魯木齊航空',
			'9H': '長安航空',
			'DR': '瑞麗航空',
			'GJ': '長龍航空',
			'NS': '河北航空',
			'EU': '成都航空',
			'BK': '奧凱航空',
			'FU': '福州航空',
			'GT': '桂林航空',
			'LT': '龍江航空',
			'RY': '江西航空',
			'QW': '青島航空',
			'SC': '山東航空',
			'ZH': '深圳航空',
			'FM': '上海航空',
			'KN': '聯合航空'
		};
		return airlineMap[iataCode] || iataCode;
	}

	/**
	 * Convert ISO 8601 duration (PT14H55M) to human-readable format
	 */
	formatDuration(isoDuration) {
		if (!isoDuration) return 'N/A';
		
		// Parse PT14H55M format
		const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
		if (!match) return isoDuration;
		
		const hours = parseInt(match[1] || '0');
		const minutes = parseInt(match[2] || '0');
		
		if (hours === 0 && minutes === 0) return 'N/A';
		
		const parts = [];
		if (hours > 0) {
			parts.push(`${hours}小時`);
		}
		if (minutes > 0) {
			parts.push(`${minutes}分鐘`);
		}
		
		return parts.join(' ');
	}

	/**
	 * Get city name from airport code
	 */
	getCityName(airportCode) {
		const cityMap = {
			// Major Asian cities
			'HKG': '香港',
			'ICN': '首爾',
			'NRT': '東京',
			'KIX': '大阪',
			'TPE': '台北',
			'SIN': '新加坡',
			'BKK': '曼谷',
			'KUL': '吉隆坡',
			'CGK': '雅加達',
			'MNL': '馬尼拉',
			'DPS': '峇里島',
			'PVG': '上海',
			'PEK': '北京',
			'CAN': '廣州',
			'SZX': '深圳',
			'CTU': '成都',
			'XIY': '西安',
			'NKG': '南京',
			'TAO': '青島',
			'TSN': '天津',
			'CKG': '重慶',
			'URC': '烏魯木齊',
			'HRB': '哈爾濱',
			'DLC': '大連',
			'SJW': '石家莊',
			'TYN': '太原',
			'INC': '銀川',
			'LHW': '蘭州',
			'XNN': '西寧',
			'KMG': '昆明',
			'LXA': '拉薩',
			'HAK': '海口',
			'FOC': '福州',
			'XMN': '廈門',
			'CSX': '長沙',
			'WUH': '武漢',
			'CGO': '鄭州',
			'JIN': '濟南',
			'YNT': '煙台',
			'WEH': '威海',
			'LYG': '連雲港',
			'NTG': '南通',
			'WNZ': '溫州',
			'NGB': '寧波',
			'HGH': '杭州',
			'WNZ': '溫州',
			'LYG': '連雲港',
			'NTG': '南通',
			'YNT': '煙台',
			'WEH': '威海',
			'JIN': '濟南',
			'CGO': '鄭州',
			'WUH': '武漢',
			'CSX': '長沙',
			'XMN': '廈門',
			'FOC': '福州',
			'HAK': '海口',
			'LXA': '拉薩',
			'KMG': '昆明',
			'XNN': '西寧',
			'LHW': '蘭州',
			'INC': '銀川',
			'TYN': '太原',
			'SJW': '石家莊',
			'DLC': '大連',
			'HRB': '哈爾濱',
			'URC': '烏魯木齊',
			'CKG': '重慶',
			'TSN': '天津',
			'TAO': '青島',
			'NKG': '南京',
			'XIY': '西安',
			'CTU': '成都',
			'SZX': '深圳',
			'CAN': '廣州',
			'PEK': '北京',
			'PVG': '上海',
			
			// Major international cities
			'SYD': '雪梨',
			'MEL': '墨爾本',
			'BNE': '布里斯班',
			'PER': '珀斯',
			'ADL': '阿德萊德',
			'CBR': '坎培拉',
			'HOB': '荷巴特',
			'DRW': '達爾文',
			'CNS': '凱恩斯',
			'TSV': '湯斯維爾',
			'OOL': '黃金海岸',
			'MCY': '陽光海岸',
			'ROK': '羅克漢普頓',
			'TSV': '湯斯維爾',
			'CNS': '凱恩斯',
			'DRW': '達爾文',
			'HOB': '荷巴特',
			'CBR': '坎培拉',
			'ADL': '阿德萊德',
			'PER': '珀斯',
			'BNE': '布里斯班',
			'MEL': '墨爾本',
			'SYD': '雪梨',
			
			// Other major cities
			'LAX': '洛杉磯',
			'JFK': '紐約',
			'LHR': '倫敦',
			'CDG': '巴黎',
			'FRA': '法蘭克福',
			'AMS': '阿姆斯特丹',
			'FCO': '羅馬',
			'MAD': '馬德里',
			'BCN': '巴塞隆納',
			'ZUR': '蘇黎世',
			'VIE': '維也納',
			'CPH': '哥本哈根',
			'ARN': '斯德哥爾摩',
			'OSL': '奧斯陸',
			'HEL': '赫爾辛基',
			'WAW': '華沙',
			'PRG': '布拉格',
			'BUD': '布達佩斯',
			'ATH': '雅典',
			'IST': '伊斯坦堡',
			'DXB': '杜拜',
			'AUH': '阿布達比',
			'DOH': '多哈',
			'KWI': '科威特',
			'BAH': '巴林',
			'JED': '吉達',
			'RUH': '利雅得',
			'CAI': '開羅',
			'JNB': '約翰內斯堡',
			'CPT': '開普敦',
			'LOS': '拉各斯',
			'NBO': '內羅畢',
			'ADD': '亞的斯亞貝巴',
			'KRT': '喀土穆',
			'KGL': '基加利',
			'DAR': '達累斯薩拉姆',
			'LUN': '盧薩卡',
			'GBE': '哈博羅內',
			'WDH': '溫得和克',
			'MPM': '馬普托',
			'BJM': '布瓊布拉',
			'KGL': '基加利',
			'DAR': '達累斯薩拉姆',
			'LUN': '盧薩卡',
			'GBE': '哈博羅內',
			'WDH': '溫得和克',
			'MPM': '馬普托',
			'BJM': '布瓊布拉',
			'NBO': '內羅畢',
			'LOS': '拉各斯',
			'CPT': '開普敦',
			'JNB': '約翰內斯堡',
			'CAI': '開羅',
			'RUH': '利雅得',
			'JED': '吉達',
			'BAH': '巴林',
			'KWI': '科威特',
			'DOH': '多哈',
			'AUH': '阿布達比',
			'DXB': '杜拜',
			'IST': '伊斯坦堡',
			'ATH': '雅典',
			'BUD': '布達佩斯',
			'PRG': '布拉格',
			'WAW': '華沙',
			'HEL': '赫爾辛基',
			'OSL': '奧斯陸',
			'ARN': '斯德哥爾摩',
			'CPH': '哥本哈根',
			'VIE': '維也納',
			'ZUR': '蘇黎世',
			'BCN': '巴塞隆納',
			'MAD': '馬德里',
			'FCO': '羅馬',
			'AMS': '阿姆斯特丹',
			'FRA': '法蘭克福',
			'CDG': '巴黎',
			'LHR': '倫敦',
			'JFK': '紐約',
			'LAX': '洛杉磯'
		};
		
		return cityMap[airportCode] || airportCode;
	}
}

// Create and export a singleton instance
export const amadeusApi = new AmadeusApiService();
