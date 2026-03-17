# Code Review Principles

Concrete examples of review principles with specific patterns to look for. Examples happen to be in Kotlin and TypeScript, but the principles apply to any language.

## Table of Contents

1. [Intent Comments](#intent-comments)
2. [Naming Conventions](#naming-conventions)
3. [No Hackiness](#no-hackiness)
4. [Documentation and Tests](#documentation-and-tests)
5. [Kotlin-Specific Patterns](#kotlin-specific-patterns)
6. [TypeScript/React Patterns](#typescriptreact-patterns)

---

## Intent Comments

Intent comments should describe **why** code exists and what business logic it implements, not just **what** the code does.

### Problem: Comment Doesn't Match Logic

Bad:
```kotlin
// Validate user input before processing
fun processUser(user: User) {
    userRepository.save(user)  // No validation happening!
}
```

Good:
```kotlin
// Skip validation for internal admin users who are pre-validated by SSO
fun processUser(user: User) {
    if (user.isAdmin) {
        userRepository.save(user)
    } else {
        validateAndSave(user)
    }
}
```

### Problem: Comment Doesn't Make Sense

Bad:
```kotlin
// Do the thing with the stuff
fun calculateDiscount(order: Order): BigDecimal {
    return order.total.multiply(BigDecimal("0.1"))
}
```

Good:
```kotlin
// Apply 10% loyalty discount for customers with 5+ previous orders
fun calculateLoyaltyDiscount(order: Order): BigDecimal {
    return order.total.multiply(LOYALTY_DISCOUNT_RATE)
}
```

### Problem: Major Typos or Grammar Issues

Bad:
```kotlin
// chek if usr has permision b4 allowing acess
fun checkAccess(user: User, resource: Resource): Boolean
```

Good:
```kotlin
// Check if user has permission before allowing access to resource
fun checkAccess(user: User, resource: Resource): Boolean
```

### When Comments Aren't Needed

Don't require comments for self-explanatory code:

Good (no comment needed):
```kotlin
fun isValidEmail(email: String): Boolean {
    return email.matches(EMAIL_REGEX)
}
```

---

## Naming Conventions

Avoid abbreviations. Use verbose, descriptive names that clearly communicate purpose.

### Variables and Parameters

Bad:
```kotlin
val msg = receiveMessage()
val usr = fetchUser(usrId)
val cfg = loadConfig()
val req = buildRequest()
```

Good:
```kotlin
val message = receiveMessage()
val user = fetchUser(userId)
val configuration = loadConfiguration()
val request = buildRequest()
```

### Functions and Methods

Bad:
```kotlin
fun procOrder(ord: Order)
fun valInput(data: String): Boolean
fun calcTotal(items: List<Item>): BigDecimal
```

Good:
```kotlin
fun processOrder(order: Order)
fun validateInput(data: String): Boolean
fun calculateTotal(items: List<Item>): BigDecimal
```

### Exceptions

Standard industry abbreviations are acceptable:
- `id` (identifier)
- `url` (Uniform Resource Locator)
- `html`, `json`, `xml` (data formats)
- `dto` (Data Transfer Object)
- `api` (Application Programming Interface)

---

## No Hackiness

Review temporary code as strictly as production code. Temporary solutions often become permanent.

### Problem: TODO Comments as Excuse for Poor Code

Bad:
```kotlin
// TODO: Fix this later, just need it working for demo
fun syncData() {
    try {
        dataService.sync()
    } catch (e: Exception) {
        // ignore errors for now
    }
}
```

Good:
```kotlin
// Log sync failures for investigation; continue processing remaining data
fun syncData() {
    try {
        dataService.sync()
    } catch (e: SyncException) {
        logger.error("Data sync failed for batch ${e.batchId}", e)
        metrics.recordSyncFailure()
        throw e
    }
}
```

### Problem: Workarounds Without Explanation

Bad:
```kotlin
fun getOrders(): List<Order> {
    Thread.sleep(1000) // fixes weird timing issue
    return orderRepository.findAll()
}
```

Good:
```kotlin
// Wait for replica lag to resolve before querying read replica
// TODO(JIRA-1234): Remove once read-after-write consistency is implemented
fun getOrders(): List<Order> {
    Thread.sleep(REPLICA_LAG_BUFFER_MS)
    return orderRepository.findAll()
}
```

### Problem: Copy-Pasted Code

Bad:
```kotlin
fun processRestaurant(restaurant: Restaurant) {
    val discount = restaurant.revenue.multiply(BigDecimal("0.1"))
    val tax = restaurant.revenue.multiply(BigDecimal("0.08"))
    // ... 50 more lines ...
}

fun processChain(chain: Chain) {
    val discount = chain.revenue.multiply(BigDecimal("0.1"))
    val tax = chain.revenue.multiply(BigDecimal("0.08"))
    // ... same 50 lines ...
}
```

Good:
```kotlin
fun calculateFinancials(revenue: BigDecimal): Financials {
    val discount = revenue.multiply(DISCOUNT_RATE)
    val tax = revenue.multiply(TAX_RATE)
    // ... shared calculation logic ...
}

fun processRestaurant(restaurant: Restaurant) {
    val financials = calculateFinancials(restaurant.revenue)
    // ... restaurant-specific logic ...
}
```

---

## Documentation and Tests

Every code change should include updated tests, documentation, and build files.

### Tests Must Be Present

New functions need tests covering happy path, edge cases, and error cases:

```kotlin
@Test
fun `calculateDiscount applies 10% for loyalty customers`() {
    val order = Order(total = BigDecimal("100.00"), isLoyaltyCustomer = true)
    val discount = calculateDiscount(order)
    assertEquals(BigDecimal("10.00"), discount)
}

@Test
fun `calculateDiscount returns zero for non-loyalty customers`() {
    val order = Order(total = BigDecimal("100.00"), isLoyaltyCustomer = false)
    val discount = calculateDiscount(order)
    assertEquals(BigDecimal.ZERO, discount)
}

@Test
fun `calculateDiscount handles null total gracefully`() {
    val order = Order(total = null, isLoyaltyCustomer = true)
    assertThrows<IllegalArgumentException> {
        calculateDiscount(order)
    }
}
```

### Test Coverage Should Be Logical

Focus on behavior coverage, not just line coverage.

Bad — only happy path:
```kotlin
@Test
fun `processPayment works`() {
    val result = processPayment(validCard)
    assertTrue(result.isSuccess)
}
```

Good — all branches and edge cases:
```kotlin
@Test fun `processPayment succeeds with valid card`() { ... }
@Test fun `processPayment fails with expired card`() { ... }
@Test fun `processPayment fails with insufficient funds`() { ... }
@Test fun `processPayment retries on network timeout`() { ... }
@Test fun `processPayment logs transaction for audit trail`() { ... }
```

### Documentation Should Explain Public APIs

For public classes and methods, include doc comments explaining purpose, parameters, return values, and exceptions.

Bad:
```kotlin
fun calculateTax(order: Order): BigDecimal {
    // implementation
}
```

Good:
```kotlin
/**
 * Calculate sales tax for the given order based on restaurant location.
 *
 * Tax rates vary by state and municipality. This function applies the
 * correct rate based on the restaurant's registered tax jurisdiction.
 *
 * @param order The order to calculate tax for. Must have a valid restaurant ID.
 * @return The tax amount in dollars and cents
 * @throws IllegalArgumentException if order.restaurantId is null
 * @throws TaxCalculationException if tax jurisdiction cannot be determined
 */
fun calculateTax(order: Order): BigDecimal {
    // implementation
}
```

### Build Files Must Be Updated

When adding, removing, or renaming files, update build configurations:
- New dependencies in `build.gradle.kts`, `package.json`, `Gemfile`, etc.
- Test files properly discovered by test runners
- README or CHANGELOG updated if public API changed

---

## Kotlin-Specific Patterns

### Use Kotlin Idioms

Bad (Java-style):
```kotlin
fun findUser(id: String): User? {
    val user = userRepository.findById(id)
    if (user != null) {
        return user
    } else {
        return null
    }
}
```

Good:
```kotlin
fun findUser(id: String): User? =
    userRepository.findById(id)
```

### Null Safety

Bad (unnecessary null checks):
```kotlin
fun getUsername(user: User?): String {
    if (user != null) {
        if (user.name != null) {
            return user.name
        }
    }
    return "Unknown"
}
```

Good (null-safe operators):
```kotlin
fun getUsername(user: User?): String =
    user?.name ?: "Unknown"
```

### Data Classes for DTOs

Bad (manual boilerplate):
```kotlin
class UserDto {
    var id: String? = null
    var name: String? = null
    override fun equals(other: Any?): Boolean { ... }
    override fun hashCode(): Int { ... }
    override fun toString(): String { ... }
}
```

Good:
```kotlin
data class UserDto(
    val id: String,
    val name: String
)
```

---

## TypeScript/React Patterns

### Type Safety

Bad (using `any`):
```typescript
function processOrder(order: any) {
    return order.total * 0.1;
}
```

Good:
```typescript
interface Order {
    id: string;
    total: number;
    items: OrderItem[];
}

function processOrder(order: Order): number {
    return order.total * 0.1;
}
```

### React Hooks Dependencies

Bad (missing dependencies):
```typescript
useEffect(() => {
    fetchUserData(userId);
}, []); // userId should be in deps!
```

Good:
```typescript
useEffect(() => {
    fetchUserData(userId);
}, [userId]);
```

### GraphQL Query Naming

Bad (generic names):
```typescript
const { data } = useQuery(GET_DATA);
```

Good (descriptive names):
```typescript
const { data: restaurantMenus } = useQuery(GET_RESTAURANT_MENUS, {
    variables: { restaurantId }
});
```

---

## General Review Checklist

When reviewing code, verify:

1. **Functional:** Code compiles, tests pass, logic is correct
2. **Clean:** Intent comments match code, verbose naming, no hacky workarounds
3. **Documented:** Tests present, public APIs documented, build files updated
4. **Optimized:** Performance is reasonable (only after 1-3 are satisfied)
