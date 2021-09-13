import streamlit as st
from multiapp import MultiApp
from apps import sequential_benchmarks, parallel_benchmarks, instrumented_pausetimes_sequential # import your app modules here

app = MultiApp()

# Add all your application here
app.add_app("Sequential Benchmarks", sequential_benchmarks.app)
app.add_app("Parallel Benchmarks", parallel_benchmarks.app)
app.add_app("Instrumented Pausetimes Sequential", instrumented_pausetimes_sequential.app)

# The main app
app.run()
