/**
 * ToteTrack DEMO seed — synthetic data for the public static demo.
 *
 * DEMO ONLY. Separate from `db/seed.ts` (the dev/testing seed), which is left
 * untouched. Every company, person, address, phone number and email below is
 * invented. Nothing here corresponds to a real customer, lead or person — the
 * production app is in daily use and none of its data appears here.
 *
 * Coverage targets (see ../../docs/plan.md "Seed data standard"):
 *   - Three years of order history so the yearly revenue view has depth, with
 *     the trailing 12 months dense enough that no month is empty.
 *   - The month in progress is topped up so the dashboard does not open on a
 *     near-empty month.
 *   - Production dates land on the next business days so the dashboard
 *     production widget and the calendar are populated, not "Nothing
 *     scheduled".
 *   - Every enum value is represented: PO status, lead status, ticket
 *     status/category/priority, customer status.
 *   - Customers carry contacts and saved delivery addresses; leads carry
 *     notes; overdue-contact and follow-up surfaces all have rows.
 *
 * Run:  npx tsx --env-file=.env.local db/seed-demo.ts
 */

import postgres from 'postgres'
import { drizzle } from 'drizzle-orm/postgres-js'
import { eq } from 'drizzle-orm'
import { addDays, format, startOfMonth, subDays } from 'date-fns'
import {
  customers,
  customerContacts,
  customerAddresses,
  orders,
  leads,
  leadNotes,
  invoices,
  supportTickets,
} from './schema'

if (!process.env.DATABASE_URL) {
  console.error('[seed-demo] DATABASE_URL is not set.')
  process.exit(1)
}

const TODAY = new Date()
const CURRENT_MONTH_START = startOfMonth(TODAY)
const HISTORY_DAYS = 365 * 3

// Deterministic PRNG (mulberry32). Reseeding produces an identical dataset,
// so screenshots taken across separate runs stay consistent.
let rngState = 20260806
function random(): number {
  rngState |= 0
  rngState = (rngState + 0x6d2b79f5) | 0
  let t = Math.imul(rngState ^ (rngState >>> 15), 1 | rngState)
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296
}

function rand(min: number, max: number): number {
  return Math.floor(random() * (max - min + 1)) + min
}

function pick<T>(arr: readonly T[]): T {
  return arr[rand(0, arr.length - 1)]!
}

function maybe(p: number): boolean {
  return random() < p
}

function isoDate(d: Date): string {
  return format(d, 'yyyy-MM-dd')
}

function money(n: number): string {
  return n.toFixed(2)
}

function slug(company: string): string {
  return company.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 20)
}

function emailFor(person: string, company: string): string {
  return `${person.split(' ')[0]!.toLowerCase()}@${slug(company)}.com`
}

// Area codes by state, so a Toledo plant does not answer on an Atlanta number.
const AREA_CODES: Record<string, readonly string[]> = {
  OH: ['216', '234', '330', '419', '440', '513', '567', '614', '740', '937'],
  PA: ['412', '484', '570', '610', '717', '724', '814', '878'],
  NY: ['315', '518', '585', '607', '716', '845'],
  MI: ['231', '269', '313', '517', '586', '616', '734', '810', '906', '989'],
  IN: ['219', '260', '317', '574', '765', '812'],
  WV: ['304', '681'],
  NC: ['336', '704', '828', '910', '919'],
  IL: ['217', '309', '312', '618', '815'],
  KY: ['270', '502', '606', '859'],
  WI: ['262', '414', '608', '715', '920'],
  MN: ['218', '320', '507', '651', '763'],
}

const FALLBACK_AREA_CODES = ['216', '330', '419', '614', '740'] as const

function phoneIn(cityState: string): string {
  const state = cityState.split(',').pop()!.trim()
  const codes = AREA_CODES[state] ?? FALLBACK_AREA_CODES
  return `(${pick(codes)}) ${rand(200, 989)}-${String(rand(1000, 9999))}`
}

/** Nudges a date off weekends — production and delivery happen on weekdays. */
function toWeekday(d: Date): Date {
  const day = d.getDay()
  if (day === 6) return addDays(d, 2)
  if (day === 0) return addDays(d, 1)
  return d
}

/** The next `count` business days at or after `from`. */
function businessDays(from: Date, count: number): Date[] {
  const out: Date[] = []
  let cursor = new Date(from)
  while (out.length < count) {
    const day = cursor.getDay()
    if (day !== 0 && day !== 6) out.push(new Date(cursor))
    cursor = addDays(cursor, 1)
  }
  return out
}

// ===== Data pools =====

const ROLES = [
  'Procurement Manager', 'Plant Manager', 'Logistics Coordinator', 'Owner',
  'Operations Director', 'Purchasing Agent', 'Warehouse Supervisor',
  'Supply Chain Lead', 'Facilities Manager',
] as const

// Long enough that no two customers share a contact — a repeated person
// across unrelated companies is the kind of detail that reads as fabricated.
const CONTACT_NAMES = [
  'Dana Whitfield', 'Marcus Okonkwo', 'Priya Raman', 'Tom Calloway',
  'Renata Vasquez', 'Ellis Brandt', 'Nadia Halloran', 'Owen Petrakis',
  'Simone Achebe', 'Curtis Nakamura', 'Hallie Brandt', 'Bernard Osei',
  'Ingrid Sandoval', 'Yusuf Karadag', 'Colette Duprey', 'Sal Moretti',
  'Beatrix Olander', 'Damaris Ocampo', 'Rory McKellen', 'Gita Bhattacharya',
  'Wes Hoffmeier', 'Odette Marchand', 'Hugo Vance', 'Marisol Quintero',
  'Lena Trowbridge', 'Amara Nwachukwu', 'Douglas Pemberton', 'Ivo Kristensen',
  'Rosa Villalobos', 'Ken Yamashita', 'Bridget Fallon', 'Emeka Balogun',
  'Sylvie Rochon', 'Norman Ashcroft', 'Tanvi Deshpande', 'Grady Sutherland',
  'Anneke de Vries', 'Miles Okafor', 'Paulina Zieliński', 'Cormac Delaney',
  'Zara Haddad', 'Reuben Sandvik', 'Camille Aubert', 'Dev Chatterjee',
  'Wendell Prosser', 'Fatima Zaidi', 'Gustav Lindholm', 'Naomi Ferreira',
] as const

const ORDER_NOTES = [
  'Gate code 4417 — call the guard shack on arrival.',
  'Dock 2 only. Dock 1 is under repair through the quarter.',
  'Customer wants a heads-up text 30 minutes out.',
  'Hi-vis and steel toe required past the yard gate.',
  'Split delivery — they will send a truck for the balance.',
  'Deliver before 11am; their receiving closes at noon.',
  'Forklift on site, no liftgate needed.',
  'Purchase order number must appear on the BOL.',
] as const

const LEAD_SOURCES = [
  'Trade show — IBC Expo', 'Referral from existing customer', 'Cold call',
  'Website enquiry form', 'LinkedIn outreach', 'Industry directory',
  'Referral from a supplier', 'Repeat contact from a past quote',
] as const

const LEAD_NOTE_SAMPLES = [
  'Good first call. They run about 40 totes a month and are unhappy with lead times.',
  'Quoted 275 reconditioned at volume. They are comparing against two other vendors.',
  'Budget is approved for next quarter. Wants to start with a trial order.',
  'Went quiet after the quote. Sent a short follow-up with updated pricing.',
  'Needs a spec sheet and a copy of our liability certificate before they can proceed.',
  'Plant manager is the decision maker, not the buyer I first spoke to.',
  'Asked about brand new 330s — margins are thinner but the volume is real.',
  'Site visit scheduled. They want to see how we grade before committing.',
  'Their current supplier missed two deliveries. Timing is good.',
] as const

const TICKETS = [
  { title: 'PO status does not refresh after marking a delivery complete', category: 'bug', priority: 'high', status: 'in_progress' },
  { title: 'Bulk import customers from a CSV', category: 'feature_request', priority: 'low', status: 'open' },
  { title: 'Notes with apostrophes fail to save on the lead detail panel', category: 'bug', priority: 'standard', status: 'resolved' },
  { title: 'Export a month invoice as PDF for the customer', category: 'feature_request', priority: 'standard', status: 'open' },
  { title: 'Revenue chart renders blank on iPad Safari', category: 'bug', priority: 'critical', status: 'in_progress' },
  { title: 'SMS reminder the morning a follow-up is due', category: 'feature_request', priority: 'low', status: 'closed' },
  { title: 'What happens to an invoiced PO if the customer cancels?', category: 'question', priority: 'standard', status: 'resolved' },
  { title: 'Calendar week strip skips a week when paging fast', category: 'bug', priority: 'high', status: 'open' },
  { title: 'Can two people use the app at the same time?', category: 'question', priority: 'low', status: 'closed' },
  { title: 'Backhaul flag should carry over when a PO is duplicated', category: 'feature_request', priority: 'high', status: 'open' },
  { title: 'Delivery address dropdown keeps an address I deleted', category: 'bug', priority: 'standard', status: 'resolved' },
  { title: 'Colour-code overdue customers on the customers list', category: 'other', priority: 'low', status: 'closed' },
] as const

type SeedSize = '275' | '330'
type SeedType = 'rebottled' | 'reconditioned' | 'brand_new'

const QTY_CELLS: ReadonlyArray<{
  size: SeedSize
  type: SeedType
  col: 'qty_275_recon' | 'qty_275_rebot' | 'qty_275_new' | 'qty_330_recon' | 'qty_330_rebot' | 'qty_330_new'
  priceCol: 'unit_price_275_recon' | 'unit_price_275_rebot' | 'unit_price_275_new' | 'unit_price_330_recon' | 'unit_price_330_rebot' | 'unit_price_330_new'
}> = [
  { size: '275', type: 'reconditioned', col: 'qty_275_recon', priceCol: 'unit_price_275_recon' },
  { size: '275', type: 'rebottled', col: 'qty_275_rebot', priceCol: 'unit_price_275_rebot' },
  { size: '275', type: 'brand_new', col: 'qty_275_new', priceCol: 'unit_price_275_new' },
  { size: '330', type: 'reconditioned', col: 'qty_330_recon', priceCol: 'unit_price_330_recon' },
  { size: '330', type: 'rebottled', col: 'qty_330_rebot', priceCol: 'unit_price_330_rebot' },
  { size: '330', type: 'brand_new', col: 'qty_330_new', priceCol: 'unit_price_330_new' },
]

function unitPriceFor(size: SeedSize, type: SeedType): number {
  if (size === '275') {
    if (type === 'brand_new') return rand(80, 110)
    if (type === 'reconditioned') return rand(55, 75)
    return rand(40, 55)
  }
  if (type === 'brand_new') return rand(110, 150)
  if (type === 'reconditioned') return rand(70, 95)
  return rand(50, 70)
}

type QtyShape = Record<(typeof QTY_CELLS)[number]['col'], number>
type PriceShape = Partial<Record<(typeof QTY_CELLS)[number]['priceCol'], string>>

const ZERO_QTY: QtyShape = {
  qty_275_recon: 0, qty_275_rebot: 0, qty_275_new: 0,
  qty_330_recon: 0, qty_330_rebot: 0, qty_330_new: 0,
}

/**
 * One PO's quantities, per-unit prices and total. Most POs are a single
 * size/type combo; a minority mix two so the multi-combo layout is exercised.
 */
function buildPo(): { qty: QtyShape; prices: PriceShape; price: number } {
  const cellCount = maybe(0.25) ? 2 : 1
  const pool = [...QTY_CELLS]
  const qty: QtyShape = { ...ZERO_QTY }
  const prices: PriceShape = {}
  let total = 0
  for (let i = 0; i < cellCount; i++) {
    const cell = pool.splice(rand(0, pool.length - 1), 1)[0]!
    const cellQty = rand(6, 34)
    const unit = unitPriceFor(cell.size, cell.type)
    qty[cell.col] = cellQty
    prices[cell.priceCol] = money(unit)
    total += cellQty * unit
  }
  return { qty, prices, price: total }
}

// ===== Customers =====

interface Archetype {
  name: string
  city: string
  active: boolean
  manualFreqDays: number | null
  firstOrderDaysAgo: number
  cadenceDays: number
  stoppedOrderingDaysAgo: number | null
  contacts: number
  addresses: number
  notes: string | null
}

const CUSTOMER_ARCHETYPES: Archetype[] = [
  { name: 'Braxton Chemical Works', city: 'Akron, OH', active: true, manualFreqDays: 30, firstOrderDaysAgo: 1020, cadenceDays: 24, stoppedOrderingDaysAgo: null, contacts: 3, addresses: 2, notes: 'Largest account. Standing order most months.' },
  { name: 'Kettleridge Coatings', city: 'Toledo, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 930, cadenceDays: 32, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 2, notes: null },
  { name: 'Palmer Agri Supply', city: 'Findlay, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 880, cadenceDays: 40, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: 'Seasonal — volume doubles Marchâ€“June.' },
  { name: 'Cortland Food Ingredients', city: 'Cortland, NY', active: true, manualFreqDays: 45, firstOrderDaysAgo: 800, cadenceDays: 44, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 1, notes: null },
  { name: 'Vandergrift Lubricants', city: 'Vandergrift, PA', active: true, manualFreqDays: null, firstOrderDaysAgo: 760, cadenceDays: 28, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 2, notes: 'Wants the PO number on every BOL.' },
  { name: 'Ashby Polymer Group', city: 'Erie, PA', active: true, manualFreqDays: null, firstOrderDaysAgo: 720, cadenceDays: 36, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Halstead Cleaning Products', city: 'Muncie, IN', active: true, manualFreqDays: 21, firstOrderDaysAgo: 690, cadenceDays: 22, stoppedOrderingDaysAgo: null, contacts: 3, addresses: 2, notes: null },
  { name: 'Nova Bay Beverages', city: 'Bay City, MI', active: true, manualFreqDays: null, firstOrderDaysAgo: 650, cadenceDays: 50, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 1, notes: 'Food-grade only. No prior chemical service.' },
  { name: 'Ridgeway Adhesives', city: 'Kalamazoo, MI', active: true, manualFreqDays: null, firstOrderDaysAgo: 610, cadenceDays: 38, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Delmar Water Treatment', city: 'Wheeling, WV', active: true, manualFreqDays: 60, firstOrderDaysAgo: 900, cadenceDays: 58, stoppedOrderingDaysAgo: 96, contacts: 2, addresses: 1, notes: 'Went quiet after a price increase. Worth a call.' },
  { name: 'Pinehurst Ink & Pigment', city: 'Fort Wayne, IN', active: true, manualFreqDays: null, firstOrderDaysAgo: 840, cadenceDays: 34, stoppedOrderingDaysAgo: 132, contacts: 1, addresses: 1, notes: null },
  { name: 'Corley Metal Finishing', city: 'Youngstown, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 700, cadenceDays: 42, stoppedOrderingDaysAgo: 61, contacts: 2, addresses: 2, notes: null },
  { name: 'Windham Dairy Cooperative', city: 'Meadville, PA', active: true, manualFreqDays: 90, firstOrderDaysAgo: 950, cadenceDays: 84, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Bellwether Specialty Fluids', city: 'Lima, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 560, cadenceDays: 30, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 1, notes: null },
  { name: 'Trenholm Soap Works', city: 'South Bend, IN', active: true, manualFreqDays: null, firstOrderDaysAgo: 500, cadenceDays: 46, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Grantley Asphalt Emulsions', city: 'Canton, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 470, cadenceDays: 54, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 2, notes: 'Shuts down for two weeks each December.' },
  { name: 'Marlowe Pharmaceutical Intermediates', city: 'Columbus, OH', active: true, manualFreqDays: 30, firstOrderDaysAgo: 420, cadenceDays: 26, stoppedOrderingDaysAgo: null, contacts: 3, addresses: 1, notes: 'Requires certificates of cleaning with every load.' },
  { name: 'Fairhaven Pet Nutrition', city: 'Elkhart, IN', active: true, manualFreqDays: null, firstOrderDaysAgo: 380, cadenceDays: 48, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Ashland Ridge Ethanol', city: 'Marion, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 330, cadenceDays: 33, stoppedOrderingDaysAgo: null, contacts: 2, addresses: 1, notes: null },
  { name: 'Quarry Point Mineral Slurry', city: 'Cambridge, OH', active: true, manualFreqDays: null, firstOrderDaysAgo: 260, cadenceDays: 52, stoppedOrderingDaysAgo: null, contacts: 1, addresses: 1, notes: null },
  { name: 'Loman Brothers Rendering', city: 'Defiance, OH', active: false, manualFreqDays: null, firstOrderDaysAgo: 980, cadenceDays: 70, stoppedOrderingDaysAgo: 300, contacts: 1, addresses: 1, notes: 'Closed the Defiance plant. Inactive.' },
  { name: 'Ferris Point Antifreeze', city: 'Battle Creek, MI', active: false, manualFreqDays: 60, firstOrderDaysAgo: 1010, cadenceDays: 64, stoppedOrderingDaysAgo: 420, contacts: 2, addresses: 1, notes: 'Moved container sourcing to a national contract.' },
]

const STREETS = [
  'Foundry Rd', 'Harbor Ave', 'County Line Rd', 'Millbrook Dr', 'Slate St',
  'Enterprise Way', 'Trellis Blvd', 'Dockside Ln', 'Kiln Ct', 'Aqueduct Rd',
  'Pressman St', 'Anodize Dr', 'Creamery Rd', 'Pumphouse Rd', 'Quarry Rd',
]

// A random five-digit number puts an Idaho ZIP on a Pennsylvania address.
// Real ZIP ranges per state keep the addresses internally consistent.
const ZIP_RANGES: Record<string, [number, number]> = {
  OH: [43000, 45999],
  PA: [15000, 19699],
  NY: [10001, 14999],
  MI: [48000, 49971],
  IN: [46000, 47997],
  WV: [24700, 26886],
  NC: [27006, 28909],
  IL: [60001, 62999],
  KY: [40003, 42788],
  WI: [53001, 54990],
  MN: [55001, 56763],
}

function addressIn(cityState: string): string {
  const state = cityState.split(',').pop()!.trim()
  const range = ZIP_RANGES[state]
  const zip = range ? rand(range[0], range[1]) : rand(10000, 99999)
  return `${rand(12, 4800)} ${pick(STREETS)}, ${cityState} ${String(zip).padStart(5, '0')}`
}

// ===== Connection =====

const client = postgres(process.env.DATABASE_URL, { prepare: false, max: 1 })
const db = drizzle(client)

async function wipe() {
  await client.unsafe(`
    TRUNCATE TABLE
      customer_contacts, customer_addresses, customers, orders,
      leads, lead_notes, invoices, support_tickets, support_attachments
    CASCADE
  `)
  console.log('  Wiped all tables.')
}

interface SeededCustomer extends Archetype {
  id: string
  addressPool: string[]
}

async function seedCustomers(): Promise<SeededCustomer[]> {
  const out: SeededCustomer[] = []
  let nameIdx = 0

  for (const arch of CUSTOMER_ARCHETYPES) {
    const [row] = await db.insert(customers).values({
      company_name: arch.name,
      status: arch.active ? 'active' : 'inactive',
      contact_frequency_days: arch.manualFreqDays,
      notes: arch.notes,
      created_at: subDays(TODAY, arch.firstOrderDaysAgo + rand(3, 20)),
    }).returning({ id: customers.id })
    const id = row!.id

    for (let i = 0; i < arch.contacts; i++) {
      const person = CONTACT_NAMES[nameIdx++ % CONTACT_NAMES.length]!
      await db.insert(customerContacts).values({
        customer_id: id,
        name: person,
        role: i === 0 ? pick(['Procurement Manager', 'Plant Manager', 'Owner']) : pick(ROLES),
        email: emailFor(person, arch.name),
        phone: phoneIn(arch.city),
        is_primary: i === 0,
      })
    }

    // Saved delivery addresses — the order form's address picker reads these,
    // so an empty pool would leave that control blank.
    const addressPool: string[] = []
    for (let i = 0; i < arch.addresses; i++) {
      const address = addressIn(arch.city)
      addressPool.push(address)
      await db.insert(customerAddresses).values({
        customer_id: id,
        address,
        last_used_at: subDays(TODAY, rand(2, 90)),
      })
    }

    out.push({ ...arch, id, addressPool })
  }
  console.log(`  Seeded ${out.length} customers with contacts and saved addresses.`)
  return out
}

// ===== Orders =====

interface SeededOrder {
  id: string
  customer_id: string
  status: 'scheduled' | 'completed' | 'cancelled'
  deliveryDate: Date
  price: number
}

function statusForAge(daysAgo: number): SeededOrder['status'] {
  // A delivery whose date has passed is done. Only the last couple of days —
  // and anything future-dated — stay open, which is what keeps the current
  // month showing both completed work and a live open-orders list.
  if (daysAgo < 3) return 'scheduled'
  if (daysAgo < 30) return maybe(0.88) ? 'completed' : 'cancelled'
  return maybe(0.94) ? 'completed' : 'cancelled'
}

let poCounter = 1

async function insertOrder(
  c: SeededCustomer,
  deliveryDate: Date,
  status: SeededOrder['status'],
  productionDate: Date | null,
  sortIndex: number | null,
): Promise<SeededOrder> {
  const { qty, prices, price } = buildPo()
  const pickupOnly = maybe(0.14)
  const [row] = await db.insert(orders).values({
    po_number: `PO-${String(poCounter).padStart(4, '0')}`,
    customer_id: c.id,
    status,
    ...qty,
    ...prices,
    price: money(price),
    pickup_only: pickupOnly,
    delivery_address: pickupOnly ? null : pick(c.addressPool),
    requested_delivery_date: isoDate(deliveryDate),
    production_date: productionDate ? isoDate(productionDate) : null,
    production_sort_index: sortIndex,
    same_day_delivery: maybe(0.18),
    backhaul: maybe(0.12),
    notes: maybe(0.3) ? pick(ORDER_NOTES) : null,
    created_at: subDays(deliveryDate, rand(4, 18)),
  }).returning({ id: orders.id })
  poCounter++
  return { id: row!.id, customer_id: c.id, status, deliveryDate, price }
}

/**
 * Production date for a PO: a weekday shortly before its delivery. Work that
 * has already happened is always dated — leaving history undated would make
 * the dashboard's "unscheduled" callout count three years of completed orders.
 * A slice of still-open POs is deliberately left undated so that callout is
 * non-zero and the calendar's unscheduled dropdown has something in it.
 */
function productionFor(deliveryDate: Date, status: SeededOrder['status']): Date | null {
  if (status === 'cancelled') return null
  if (status === 'scheduled' && maybe(0.35)) return null
  return toWeekday(subDays(deliveryDate, rand(1, 3)))
}

async function seedOrders(customerSeeds: SeededCustomer[]): Promise<SeededOrder[]> {
  const all: SeededOrder[] = []

  for (const c of customerSeeds) {
    // -18 lets active customers carry future-dated scheduled POs.
    const endDaysAgo = c.stoppedOrderingDaysAgo ?? -18
    let offset = Math.min(c.firstOrderDaysAgo, HISTORY_DAYS)
    while (offset > endDaysAgo) {
      const deliveryDate = toWeekday(addDays(subDays(TODAY, offset), rand(-3, 3)))
      const daysAgo = Math.floor((TODAY.getTime() - deliveryDate.getTime()) / 86400000)
      const status = statusForAge(daysAgo)
      all.push(await insertOrder(c, deliveryDate, status, productionFor(deliveryDate, status), null))
      offset -= Math.round(c.cadenceDays + rand(-6, 6))
    }
  }
  console.log(`  Seeded ${all.length} orders.`)
  return all
}

/**
 * Tops up the month in progress. Cadence-driven scheduling alone can leave the
 * first days of a month nearly empty, which reads as a broken app rather than
 * an early month.
 */
async function topUpCurrentMonth(customerSeeds: SeededCustomer[], all: SeededOrder[]): Promise<void> {
  const existing = all.filter((o) => o.deliveryDate >= CURRENT_MONTH_START).length
  const target = Math.max(10, Math.min(TODAY.getDate(), 18))
  if (existing >= target) return

  const active = customerSeeds.filter((c) => c.active && c.stoppedOrderingDaysAgo === null)
  const span = Math.max(1, Math.floor((TODAY.getTime() - CURRENT_MONTH_START.getTime()) / 86400000))
  for (let i = 0; i < target - existing; i++) {
    const c = active[i % active.length]!
    const deliveryDate = toWeekday(addDays(CURRENT_MONTH_START, (i * 2) % (span + 1)))
    const daysAgo = Math.floor((TODAY.getTime() - deliveryDate.getTime()) / 86400000)
    const status = statusForAge(daysAgo)
    all.push(await insertOrder(c, deliveryDate, status, productionFor(deliveryDate, status), null))
  }
  console.log(`  Topped up the current month to ${target} orders.`)
}

/**
 * Guarantees a live pipeline of future-dated open POs.
 *
 * Cadence alone puts only a handful of orders ahead of today, which starves
 * three surfaces at once: the open-orders widget, the production calendar and
 * the unscheduled callout. A real board always has a few weeks of committed
 * work in front of it.
 */
async function ensureOpenPipeline(customerSeeds: SeededCustomer[], all: SeededOrder[]): Promise<void> {
  const open = all.filter((o) => o.status === 'scheduled').length
  const TARGET_OPEN = 32
  if (open >= TARGET_OPEN) return

  const active = customerSeeds.filter((c) => c.active && c.stoppedOrderingDaysAgo === null)
  for (let i = 0; open + i < TARGET_OPEN; i++) {
    const c = active[i % active.length]!
    // Spread across the next five weeks so the calendar pages have content
    // either side of the visible week.
    const deliveryDate = toWeekday(addDays(TODAY, 1 + ((i * 3) % 34)))
    all.push(await insertOrder(c, deliveryDate, 'scheduled', null, null))
  }
  console.log(`  Extended the open pipeline to ${TARGET_OPEN} POs.`)
}

/**
 * Fills the production calendar and the dashboard's production widget.
 *
 * This re-dates orders that already exist rather than inserting new ones —
 * an earlier version created a batch per day, which piled a month's worth of
 * extra revenue into the current month and left the trend chart with one
 * absurd bar. Orders already carry a production_date from `productionFor`;
 * this only redistributes the ones near today so no visible day is empty.
 */
async function scheduleProduction(): Promise<void> {
  // Two weeks of business days from a week back, so the calendar has both
  // completed history and upcoming work either side of today.
  // A week back and a fortnight forward — the span the calendar's week strip
  // reaches with one arrow press in either direction.
  const days = businessDays(subDays(TODAY, 7), 15)

  // Every order that could plausibly be produced somewhere in the window.
  // Production runs ahead of delivery, so a day is filled from orders
  // delivering within the following fortnight — matching per day rather than
  // walking one global list, which previously starved whichever end of the
  // window came last.
  const pool = (await client.unsafe(`
    SELECT id, requested_delivery_date::text AS delivery
    FROM orders
    WHERE status <> 'cancelled'
      AND requested_delivery_date BETWEEN '${isoDate(subDays(TODAY, 10))}' AND '${isoDate(addDays(TODAY, 45))}'
    ORDER BY requested_delivery_date
  `)) as unknown as Array<{ id: string; delivery: string }>

  // Reserved so the calendar's unscheduled dropdown and the dashboard's
  // unscheduled callout are never empty.
  const UNSCHEDULED_RESERVE = 6
  const reserved = new Set(pool.slice(-UNSCHEDULED_RESERVE).map((r) => r.id))
  const taken = new Set<string>()
  let placed = 0

  // Spread the pool evenly rather than front-loading it — filling the first
  // days greedily left the back half of the window reading "Nothing
  // scheduled" on a board that has plenty of work in it.
  const perDayBase = Math.max(2, Math.floor((pool.length - UNSCHEDULED_RESERVE) / days.length))

  for (const day of days) {
    const dayIso = isoDate(day)
    const latest = isoDate(addDays(day, 14))
    const perDay = perDayBase + (maybe(0.4) ? 1 : 0)
    let slot = 0
    for (const row of pool) {
      if (slot >= perDay) break
      if (taken.has(row.id) || reserved.has(row.id)) continue
      if (row.delivery < dayIso || row.delivery > latest) continue
      taken.add(row.id)
      await db.update(orders)
        .set({ production_date: dayIso, production_sort_index: slot })
        .where(eq(orders.id, row.id))
      slot++
      placed++
    }
  }

  // Clear the reserve in case `productionFor` had already dated those rows.
  for (const id of reserved) {
    await db.update(orders)
      .set({ production_date: null, production_sort_index: null })
      .where(eq(orders.id, id))
  }

  console.log(`  Placed ${placed} existing orders onto the production calendar.`)
}

// ===== Invoices =====

async function seedInvoices(orderSeeds: SeededOrder[]): Promise<void> {
  const groups = new Map<string, SeededOrder[]>()
  for (const o of orderSeeds) {
    if (o.status !== 'completed') continue
    // The month in progress is not invoiced yet — that is what makes the
    // "current month" row on the invoices screen meaningful.
    if (o.deliveryDate >= CURRENT_MONTH_START) continue
    const key = format(o.deliveryDate, 'yyyy-MM')
    const arr = groups.get(key) ?? []
    arr.push(o)
    groups.set(key, arr)
  }

  const months = [...groups.keys()].sort()
  let invNum = 1
  for (const yearMonth of months) {
    const groupOrders = groups.get(yearMonth)!
    const total = groupOrders.reduce((s, o) => s + o.price, 0)
    const [inv] = await db.insert(invoices).values({
      invoice_number: `INV-${String(invNum).padStart(4, '0')}`,
      billing_month: `${yearMonth}-01`,
      total_amount: money(total),
    }).returning({ id: invoices.id })

    for (const o of groupOrders) {
      await db.update(orders)
        .set({ status: 'invoiced', invoice_id: inv!.id })
        .where(eq(orders.id, o.id))
    }
    invNum++
  }
  console.log(`  Seeded ${months.length} monthly invoices.`)
}

// ===== Leads =====

interface LeadArchetype {
  name: string
  company: string
  title: string
  /** Two-letter state. Leads carry no address; this only anchors the area code. */
  state: string
  status: 'hot' | 'warm' | 'cold'
  daysUntilFollowUp: number | null
  noteCount: number
}

const LEAD_ARCHETYPES: LeadArchetype[] = [
  { name: 'Elena Marchetti', company: 'Northgate Resin Partners', state: 'OH', title: 'Procurement Director', status: 'hot', daysUntilFollowUp: -6, noteCount: 3 },
  { name: 'Desmond Frye', company: 'Cobalt Line Solvents', state: 'PA', title: 'Operations Lead', status: 'hot', daysUntilFollowUp: -2, noteCount: 3 },
  { name: 'Junia Castellanos', company: 'Harrow Valley Cider', state: 'MI', title: 'Owner', status: 'hot', daysUntilFollowUp: 0, noteCount: 2 },
  { name: 'Ben Oyelaran', company: 'Prairie Fork Fertilizer', state: 'IL', title: 'Purchasing Manager', status: 'hot', daysUntilFollowUp: 2, noteCount: 2 },
  { name: 'Nadia Kirilenko', company: 'Sable Creek Detergents', state: 'KY', title: 'Plant Manager', status: 'warm', daysUntilFollowUp: -1, noteCount: 2 },
  { name: 'Roland Beaumont', company: 'Meridian Plating Supply', state: 'NY', title: 'General Manager', status: 'warm', daysUntilFollowUp: 5, noteCount: 1 },
  { name: 'Farrah Osman', company: 'Kestrel Labs Reagents', state: 'IN', title: 'Sourcing Lead', status: 'warm', daysUntilFollowUp: 9, noteCount: 2 },
  { name: 'Gunnar Sjoberg', company: 'Old Mill Flavor House', state: 'NY', title: 'Operations Director', status: 'warm', daysUntilFollowUp: 16, noteCount: 1 },
  { name: 'Tamsin Reyes', company: 'Bexley Road Sealants', state: 'OH', title: 'Buyer', status: 'warm', daysUntilFollowUp: 23, noteCount: 1 },
  { name: 'Achille Duval', company: 'Ironwood Pulp Chemicals', state: 'WI', title: 'Supply Chain Lead', status: 'cold', daysUntilFollowUp: 34, noteCount: 1 },
  { name: 'Petra Novakova', company: 'Sandhill Ag Cooperative', state: 'MI', title: 'Procurement Agent', status: 'cold', daysUntilFollowUp: 45, noteCount: 0 },
  { name: 'Isaiah Bergstrom', company: 'Cormorant Marine Coatings', state: 'MN', title: 'Plant Manager', status: 'cold', daysUntilFollowUp: null, noteCount: 1 },
  { name: 'Margit Hollander', company: 'Vale Street Brewing', state: 'OH', title: 'Owner', status: 'cold', daysUntilFollowUp: null, noteCount: 0 },
  { name: 'Terrence Amadi', company: 'Halloway Industrial Waxes', state: 'WV', title: 'Facilities Manager', status: 'cold', daysUntilFollowUp: 60, noteCount: 1 },
]

async function seedLeads(customerSeeds: SeededCustomer[]): Promise<void> {
  for (const a of LEAD_ARCHETYPES) {
    const followUp = a.daysUntilFollowUp !== null ? isoDate(addDays(TODAY, a.daysUntilFollowUp)) : null
    const [row] = await db.insert(leads).values({
      name: a.name,
      title: a.title,
      company: a.company,
      email: emailFor(a.name, a.company),
      phone: maybe(0.8) ? phoneIn(a.state) : null,
      status: a.status,
      lead_source: pick(LEAD_SOURCES),
      next_follow_up_date: followUp,
      next_action_type: followUp ? pick(['call', 'email', 'visit']) : null,
      created_at: subDays(TODAY, rand(20, 420)),
    }).returning({ id: leads.id })

    for (let i = 0; i < a.noteCount; i++) {
      await db.insert(leadNotes).values({
        lead_id: row!.id,
        content: pick(LEAD_NOTE_SAMPLES),
        created_at: subDays(TODAY, rand(2, 120)),
      })
    }
  }

  // Converted leads point at real customers — this is what makes the
  // "converted" filter on the leads screen non-empty.
  let converted = 0
  for (const customer of customerSeeds.slice(0, 4)) {
    const person = CONTACT_NAMES[(converted + 11) % CONTACT_NAMES.length]!
    const [row] = await db.insert(leads).values({
      name: person,
      title: pick(ROLES),
      company: customer.name,
      email: emailFor(person, customer.name),
      phone: phoneIn(customer.city),
      status: 'converted',
      lead_source: pick(LEAD_SOURCES),
      converted_customer_id: customer.id,
      created_at: subDays(TODAY, customer.firstOrderDaysAgo + rand(10, 40)),
    }).returning({ id: leads.id })
    await db.insert(leadNotes).values({
      lead_id: row!.id,
      content: 'Converted after a trial order. Now on a regular cycle.',
      created_at: subDays(TODAY, customer.firstOrderDaysAgo),
    })
    converted++
  }
  console.log(`  Seeded ${LEAD_ARCHETYPES.length + converted} leads (${converted} converted).`)
}

// ===== Support =====

async function seedSupport(): Promise<void> {
  for (const t of TICKETS) {
    await db.insert(supportTickets).values({
      title: t.title,
      category: t.category,
      priority: t.priority,
      description:
        'Reported from daily use. Steps to reproduce are in the title; happy to walk through it on a call if that is quicker.',
      status: t.status,
      developer_notes:
        t.status === 'resolved' || t.status === 'closed'
          ? 'Fixed and verified. Shipped in the last release.'
          : t.status === 'in_progress'
            ? 'Reproduced locally. Fix in progress.'
            : null,
      created_at: subDays(TODAY, rand(3, 200)),
    })
  }
  console.log(`  Seeded ${TICKETS.length} support tickets.`)
}

// ===== Coverage report =====

async function report(): Promise<void> {
  const one = async (sql: string): Promise<number> =>
    Number((await client.unsafe(sql))[0]!.count)

  const counts = {
    customers: await one('SELECT count(*) FROM customers'),
    contacts: await one('SELECT count(*) FROM customer_contacts'),
    addresses: await one('SELECT count(*) FROM customer_addresses'),
    orders: await one('SELECT count(*) FROM orders'),
    invoices: await one('SELECT count(*) FROM invoices'),
    leads: await one('SELECT count(*) FROM leads'),
    tickets: await one('SELECT count(*) FROM support_tickets'),
  }
  console.log('\nSeed complete.')
  for (const [k, v] of Object.entries(counts)) {
    console.log(`  ${k.padEnd(12)} ${String(v).padStart(5)}`)
  }

  const problems: string[] = []

  const check = async (label: string, sql: string, min = 1) => {
    const n = await one(sql)
    if (n < min) problems.push(`${label} (found ${n}, need ${min})`)
    return n
  }

  for (const s of ['scheduled', 'completed', 'cancelled', 'invoiced']) {
    await check(`no orders with status '${s}'`, `SELECT count(*) FROM orders WHERE status = '${s}'`)
  }
  for (const s of ['hot', 'warm', 'cold', 'converted']) {
    await check(`no leads with status '${s}'`, `SELECT count(*) FROM leads WHERE status = '${s}'`)
  }
  for (const s of ['open', 'in_progress', 'resolved', 'closed']) {
    await check(`no tickets with status '${s}'`, `SELECT count(*) FROM support_tickets WHERE status = '${s}'`)
  }
  for (const s of ['bug', 'feature_request', 'question', 'other']) {
    await check(`no tickets in category '${s}'`, `SELECT count(*) FROM support_tickets WHERE category = '${s}'`)
  }
  for (const s of ['active', 'inactive']) {
    await check(`no customers with status '${s}'`, `SELECT count(*) FROM customers WHERE status = '${s}'`)
  }

  await check(
    'the dashboard month view would look empty',
    `SELECT count(*) FROM orders WHERE requested_delivery_date >= '${isoDate(CURRENT_MONTH_START)}'`,
    8,
  )
  // The calendar opens on the current week and the dashboard widget shows the
  // next two business days. One populated column beside "Nothing scheduled"
  // is exactly the half-empty look to avoid, so every business day from a
  // week back through next week must carry work.
  for (const day of businessDays(subDays(TODAY, 7), 12)) {
    await check(
      `nothing in production on ${isoDate(day)} — the dashboard widget would show "Nothing scheduled"`,
      `SELECT count(*) FROM orders WHERE production_date = '${isoDate(day)}'`,
      2,
    )
  }
  await check(
    'no leads are due or overdue — the follow-up widget would be empty',
    `SELECT count(*) FROM leads WHERE next_follow_up_date <= '${isoDate(TODAY)}' AND status <> 'converted'`,
    2,
  )
  await check(
    'no open orders — the dashboard open-orders widget would be empty',
    `SELECT count(*) FROM orders WHERE status = 'scheduled'`,
    5,
  )
  await check(
    'nothing unscheduled — the calendar\'s unscheduled dropdown would be empty',
    `SELECT count(*) FROM orders WHERE status <> 'cancelled' AND production_date IS NULL`,
    3,
  )

  // Every month of the trailing year must have orders, or the 12-month
  // revenue chart renders a gap.
  for (let i = 0; i < 12; i++) {
    const monthStart = startOfMonth(subDays(CURRENT_MONTH_START, i * 28 + 1))
    const nextStart = startOfMonth(addDays(monthStart, 40))
    await check(
      `no orders in ${format(monthStart, 'yyyy-MM')} — the revenue chart would have a gap`,
      `SELECT count(*) FROM orders WHERE requested_delivery_date >= '${isoDate(monthStart)}' AND requested_delivery_date < '${isoDate(nextStart)}'`,
    )
  }

  const dupContacts = (await client.unsafe(
    'SELECT count(*)::int AS count FROM (SELECT name FROM customer_contacts GROUP BY name HAVING count(*) > 1) d',
  )) as unknown as Array<{ count: number }>
  if ((dupContacts[0]?.count ?? 0) > 0) {
    problems.push(
      `${dupContacts[0]!.count} contact name(s) appear at more than one customer — a repeated person across unrelated companies reads as fabricated`,
    )
  }

  // A month that dwarfs its neighbours makes the trend chart look fabricated.
  // This caught a scheduling bug that piled an extra month of orders into the
  // current one, so it stays as a guard.
  const monthly = (await client.unsafe(`
    SELECT to_char(requested_delivery_date, 'YYYY-MM') AS m, SUM(price)::float AS total
    FROM orders
    WHERE status <> 'cancelled'
      AND requested_delivery_date >= '${isoDate(subDays(CURRENT_MONTH_START, 400))}'
    GROUP BY 1 ORDER BY 1
  `)) as unknown as Array<{ m: string; total: number }>
  const closed = monthly.slice(0, -1)
  const current = monthly.at(-1)
  if (closed.length >= 6 && current) {
    const avg = closed.reduce((s, r) => s + r.total, 0) / closed.length
    // Month-to-date is expected to be below a full month; the ceiling is the
    // one that matters.
    if (current.total > avg * 1.8) {
      problems.push(
        `${current.m} revenue is ${(current.total / avg).toFixed(1)}x the trailing monthly average — the trend chart would show one implausible spike`,
      )
    }
  }

  if (problems.length) {
    console.error('\nCOVERAGE FAILURES:')
    for (const p of problems) console.error(`  - ${p}`)
    process.exit(1)
  }
  console.log('\nCoverage checks passed — no empty screens.')
}

// ===== Main =====

async function main() {
  const host = process.env.DATABASE_URL!.split('@')[1]?.split('/')[0] ?? 'unknown'
  console.log(`[seed-demo] Target: ${host}`)
  try {
    await wipe()
    const customerSeeds = await seedCustomers()
    const orderSeeds = await seedOrders(customerSeeds)
    await topUpCurrentMonth(customerSeeds, orderSeeds)
    await ensureOpenPipeline(customerSeeds, orderSeeds)
    await scheduleProduction()
    await seedInvoices(orderSeeds)
    await seedLeads(customerSeeds)
    await seedSupport()
    await report()
  } finally {
    await client.end()
  }
}

main().catch((err) => {
  console.error('[seed-demo] Failed:', err)
  process.exit(1)
})
