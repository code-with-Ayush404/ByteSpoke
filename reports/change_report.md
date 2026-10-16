# Customer Dimension Change Report

- Unique customers: **4**
- Total versions: **6**
- Current versions: **4**
- Change events: **6**

## Events

### INSERT — C1001 (2026-01-01)
- Changed fields: customer_name, city, segment
- Before: `null`
- After: `{"city": "Lucknow", "customer_name": "Aarav Sharma", "segment": "Standard"}`

### INSERT — C1002 (2026-01-01)
- Changed fields: customer_name, city, segment
- Before: `null`
- After: `{"city": "Kanpur", "customer_name": "Meera Singh", "segment": "Premium"}`

### INSERT — C1003 (2026-01-01)
- Changed fields: customer_name, city, segment
- Before: `null`
- After: `{"city": "Noida", "customer_name": "Kabir Verma", "segment": "Standard"}`

### UPDATE — C1001 (2026-03-01)
- Changed fields: city, segment
- Before: `{"city": "Lucknow", "customer_name": "Aarav Sharma", "segment": "Standard"}`
- After: `{"city": "Delhi", "customer_name": "Aarav Sharma", "segment": "Premium"}`

### UPDATE — C1003 (2026-03-01)
- Changed fields: segment
- Before: `{"city": "Noida", "customer_name": "Kabir Verma", "segment": "Standard"}`
- After: `{"city": "Noida", "customer_name": "Kabir Verma", "segment": "Premium"}`

### INSERT — C1004 (2026-03-01)
- Changed fields: customer_name, city, segment
- Before: `null`
- After: `{"city": "Gorakhpur", "customer_name": "Ishita Gupta", "segment": "Standard"}`

