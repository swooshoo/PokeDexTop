
# PokeDexTop : A Desktop National Pokedex 

<img align="right" width="100" height="100" src="assets/pokeball.png">
<p>A National Pokedex for Pokemon TCG Collectors. Add cards to a your collection from current and vintage sets, and build your dream national pokedex collection without redundant websites. <br>  

Upon a friend group challenging eachother to cultivate a TCG national pokedex generation by generation over months per gen, I was inspired to code a digital binder to track, display, search, and share admirable TCG cards and binder pages. </p> 

## Features

- A digital binder organized by Pokedex number and split into generations.
- A 'Search by Set' tab that allows you to browse through TCG sets.
- A 'Search by Pokemon' tab that allows you to search for all cards pertaining to certain Pokemon.
- A button to add cards from either Search tabs to your digital binder.

<img width="300" alt="Screenshot 2025-05-14 at 5 53 53 PM" src="https://github.com/user-attachments/assets/653f6cd3-4f99-4503-a3bc-7a9ecd918fb6" />

- Select and export cards by generation, with or without complete Pokedex generations!

<img width="300" alt="Screenshot 2025-05-14 at 5 54 38 PM" src="https://github.com/user-attachments/assets/e2fbdb6d-fef6-46bd-b770-9a59d4c9a9d7" />

## Features to Work on (Refer to Issues)

- Hover and examine cards for further detail.
- Remove existing cards in your digital binder.


# Architecture & Data Pipeline Redesign (June 2025 - August 2025)
Completely revamping the desktop app by rebuilding the data infrastructure to handle API integration with improved reliability, deduplication, and performance optimization. 

## Advantages of the Redesigned System Architecture

### **Scalability & Performance**

- **Lightweight Client**: Frontend downloads ~50MB instead of 5GB, dramatically reducing installation time and storage requirements
- **Dynamic Data Loading**: Real-time access to the latest Pokemon cards and sets without requiring app updates
- **Intelligent Caching**: Local caching with background updates provides offline functionality while maintaining data freshness
- **Horizontal Scaling**: Backend can handle thousands of users simultaneously with proper load balancing

### **Data Freshness & Reliability**

- **Always Current**: Users automatically get new card releases, price updates, and metadata corrections
- **Data Quality Assurance**: Automated ETL pipelines ensure consistent, validated data across all users
- **Backup & Recovery**: Cloud-based data storage with automated backups prevents data loss
- **Version Control**: Complete audit trail of data changes with rollback capabilities

### **Development & Maintenance**

- **Separation of Concerns**: Frontend and backend can be developed, tested, and deployed independently
- **API-First Design**: Enables future mobile apps, web interfaces, or third-party integrations
- **Automated Testing**: CI/CD pipelines catch bugs before deployment to production
- **Monitoring & Observability**: Real-time insights into system performance and user behavior

### **User Experience Enhancements**

- **Faster Initial Setup**: Quick download and installation gets users started immediately
- **Seamless Updates**: Backend improvements and new features appear automatically
- **Multi-Device Sync**: User collections and preferences sync across devices (future capability)
- **Community Features**: Shared collections, trading suggestions, and market insights (future capability)

### **Business Intelligence & Analytics**

- **Usage Analytics**: Understanding which Pokemon and sets are most popular
- **Performance Metrics**: Real-time monitoring of system health and user satisfaction
- **Data-Driven Features**: Machine learning recommendations for card collecting strategies
- **Market Integration**: Live price data and collection value tracking

## Potential New Challenges

### **Infrastructure Complexity**

- **Multi-Service Architecture**: Requires managing databases, APIs, ETL pipelines, and monitoring systems
- **Cloud Costs**: Ongoing operational expenses for hosting, storage, and data transfer
- **DevOps Requirements**: Need expertise in deployment, scaling, and incident response
- **Security Considerations**: API authentication, data encryption, and protection against attacks

### **Network Dependencies**

- **Internet Requirement**: Core functionality requires stable internet connection
- **API Reliability**: System availability depends on backend service uptime
- **Latency Considerations**: Geographic distance to servers may affect performance
- **Graceful Degradation**: Need robust offline modes when connectivity is poor

### **Development Overhead**

- **Learning Curve**: Requires mastering additional technologies (databases, cloud services, ETL tools)
- **Deployment Complexity**: Multiple services need coordinated releases and rollback strategies
- **Testing Challenges**: Integration testing across frontend, API, and database layers
- **Documentation Burden**: Need comprehensive API docs and system architecture diagrams

### **Data Management Responsibilities**

- **Privacy Compliance**: GDPR, CCPA, and other regulations for user data handling
- **Data Retention Policies**: Managing storage costs while maintaining historical data
- **Migration Challenges**: Moving users from local data to cloud-based system
- **Backup Strategies**: Ensuring business continuity and disaster recovery
## Long-Term Strategic Benefits

### **Portfolio & Career Development**

- **Industry-Standard Architecture**: Demonstrates proficiency with modern data engineering practices
- **Cloud-Native Experience**: Hands-on experience with AWS, databases, and DevOps tools
- **Full-Stack Capability**: Shows ability to design systems from data ingestion to user interface
- **Production Mindset**: Understanding of monitoring, testing, and operational excellence

### **Project Evolution Opportunities**

- **Machine Learning Integration**: Recommendation engines, price prediction models, and collection optimization
- **Mobile Application**: Native iOS/Android apps sharing the same backend infrastructure
- **Marketplace Features**: Trading platform, auction integration, and collection valuation tools
- **Community Platform**: User profiles, collection sharing, and social features

