export type AirlineOption = {
  code: string;
  name: string;
};

export const airlineOptions: AirlineOption[] = [
  { code: 'AA', name: 'American Airlines' },
  { code: 'AC', name: 'Air Canada' },
  { code: 'AF', name: 'Air France' },
  { code: 'AI', name: 'Air India' },
  { code: 'BA', name: 'British Airways' },
  { code: 'BR', name: 'EVA Air' },
  { code: 'CA', name: 'Air China' },
  { code: 'CX', name: 'Cathay Pacific' },
  { code: 'DL', name: 'Delta Air Lines' },
  { code: 'EK', name: 'Emirates' },
  { code: 'EY', name: 'Etihad Airways' },
  { code: 'GA', name: 'Garuda Indonesia' },
  { code: 'JL', name: 'Japan Airlines' },
  { code: 'KE', name: 'Korean Air' },
  { code: 'LH', name: 'Lufthansa' },
  { code: 'NH', name: 'ANA All Nippon Airways' },
  { code: 'NZ', name: 'Air New Zealand' },
  { code: 'QF', name: 'Qantas' },
  { code: 'QR', name: 'Qatar Airways' },
  { code: 'SQ', name: 'Singapore Airlines' },
  { code: 'TK', name: 'Turkish Airlines' },
  { code: 'UA', name: 'United Airlines' },
  { code: 'VS', name: 'Virgin Atlantic' }
];

export const airlineOptionsMap = new Map(airlineOptions.map((airline) => [airline.code, airline]));

