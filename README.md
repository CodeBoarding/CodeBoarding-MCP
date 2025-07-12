We adopt the formatting standard from [llmstxt.org](https://llmstxt.org/) and provide two tools for generating onboarding context:

We use [GeneratedOnBoardings](https://github.com/CodeBoarding/GeneratedOnBoardings) for repositories that already include generated onboarding data. If such data is not available, you can generate it using our [website demo](https://www.codeboarding.org/demo).

### Tools

1. **`get_onboarding_context_with_code`**  
   Generates onboarding context **with** code references (suitable for larger contexts, typically > 100k tokens).

2. **`get_onboarding_context_without_code`**  
   Generates onboarding context **without** code references (leaner format).
