# Quick Start Guide - Architecture Synthesis Platform

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
cd Backend
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
uvicorn app:app --reload
```

The server will start at `http://localhost:8000`

### Step 3: Test the Pipeline
```bash
python test_synthesis.py
```

You should see output like:
```
============================================================
Testing Architecture Synthesis Pipeline
============================================================

1. Loading Master Request JSON...
   ✓ Loaded intent for sector: Fintech

2. Loading policies...
   ✓ Loaded 1 policy files
   ✓ Merged into 8 rules

3. Selecting architecture blocks...
   ✓ Selected 7 blocks

...

SYNTHESIS COMPLETE!
Architecture ID: arch_abc123
Estimated Cost: $5500/month
============================================================
```

## 🔥 Try the API

### Generate Architecture from Intent

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/synthesize
```

**Using Python:**
```python
import requests

response = requests.post("http://localhost:8000/api/synthesize")
result = response.json()

print(f"Architecture ID: {result['architecture_id']}")
print(f"Blocks: {result['selected_architecture']['selected_blocks']}")
print(f"Compliance: {result['compliance_report']['compliance_status']}")
print(f"Cost: ${result['resolved_architecture']['estimated_monthly_cost_usd']}/month")
```

### Response Structure
```json
{
  "architecture_id": "arch_abc123",
  "selected_architecture": {
    "selected_blocks": ["waf_layer", "api_gateway", ...],
    "deployment_topology": {
      "regions": ["ap-south-1", "ap-southeast-1"],
      "active_active": true,
      "multi_az": true
    },
    "estimated_monthly_cost_usd": 5500
  },
  "graph": {
    "nodes": [
      {
        "id": "waf_layer",
        "category": "security",
        "region": "ap-south-1",
        "data": {"label": "WAF"}
      },
      ...
    ],
    "edges": [
      {
        "id": "e0",
        "from": "client",
        "to": "waf_layer",
        "protocol": "https"
      },
      ...
    ]
  },
  "compliance_report": {
    "compliance_status": "compliant",
    "risk_score": 0.0,
    "checks": [...],
    "violations": []
  },
  "resolved_architecture": {
    "resolved_products": [
      {
        "id": "waf_layer",
        "resolved_products": [
          {
            "provider": "aws",
            "product_name": "AWS WAF",
            "recommended": true
          }
        ]
      },
      ...
    ]
  }
}
```

## 📊 Understanding the Output

### Selected Architecture
- **selected_blocks**: List of architecture building blocks chosen
- **deployment_topology**: Regions, HA, replication settings
- **scoring_summary**: Performance, cost, compliance scores
- **estimated_monthly_cost_usd**: Total estimated cost

### Graph
- **nodes**: Architecture components (compute, data, network, etc.)
- **edges**: Connections between components (traffic, data, replication)

### Compliance Report
- **compliance_status**: "compliant" or "non_compliant"
- **risk_score**: 0.0 (compliant) to 1.0 (high risk)
- **checks**: Individual rule evaluations
- **violations**: List of compliance violations (if any)

### Resolved Architecture
- **resolved_products**: Actual cloud products for each node
- Maps to AWS, Your Cloud, or other providers
- Shows recommended products and alternatives

## 🎯 Common Use Cases

### 1. Generate Architecture for Web App
The existing Master Request JSON is already configured for a web application.
Just call `/api/synthesize` and you'll get:
- WAF for security
- API Gateway for routing
- Compute for application
- Database for data
- Cache for performance
- Logging for audit

### 2. Check Compliance
The compliance report shows if your architecture meets BFSI requirements:
- Encryption at rest/transit
- Multi-region deployment
- No public database access
- WAF before API Gateway

### 3. Compare Cloud Providers
The resolved products show options for:
- AWS (recommended if specified in preferences)
- Your Cloud (alternative)
- Cost comparison

### 4. Estimate Costs
Get monthly cost estimates based on:
- Selected blocks
- Instance counts
- Resource configurations

## 🔧 Customization

### Add a New Policy
Create `policies/sectors/healthcare.json`:
```json
{
  "policy_metadata": {
    "policy_id": "healthcare_baseline_v1",
    "sector": "Healthcare",
    ...
  },
  "rules": [...]
}
```

### Add a New Block
Edit `blocks/block_registry.json` and add:
```json
{
  "block_id": "serverless_compute",
  "category": "compute",
  "capabilities_provided": {
    "serverless": true,
    "auto_scaling": true
  },
  ...
}
```

### Add a New Product Catalog
Create `products/azure_catalog.json`:
```json
{
  "provider": "azure",
  "products": [...]
}
```

## 📝 Example Workflow

1. **User completes questionnaire** → Generates Master Request JSON
2. **Call `/api/synthesize`** → Platform generates architecture
3. **Review compliance report** → Check for violations
4. **View graph topology** → Understand architecture
5. **Check product mappings** → See AWS/Your Cloud options
6. **Review cost estimate** → Validate budget
7. **Deploy (future)** → Execute deployment plan

## 🐛 Troubleshooting

### Error: "No policy found for sector"
- Check that `policies/sectors/{sector}.json` exists
- Sector name must match (case-insensitive)

### Error: "Block registry not found"
- Ensure `blocks/block_registry.json` exists
- Check file permissions

### Error: "No Master Request JSON available"
- Complete the questionnaire first
- Or manually POST to `/api/intent-json`

### Compliance violations
- Review the compliance report
- Check which rules failed
- Adjust intent or policy as needed

## 📚 Learn More

- **README_ARCHITECTURE_SYNTHESIS.md**: Complete documentation
- **IMPLEMENTATION_SUMMARY.md**: Implementation details
- **ARCHITECTURE_SYNTHESIS_PLAN 2.pdf**: Original specification

## 🎉 You're Ready!

The Architecture Synthesis Platform is now running and ready to generate cloud architectures from user intent.

**Next steps:**
1. Try the test script
2. Call the API endpoint
3. Review the generated architecture
4. Customize policies, blocks, or products as needed

Happy architecting! 🏗️
