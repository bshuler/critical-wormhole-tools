import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';

import HomeScreen from './screens/HomeScreen';
import BrowserScreen from './screens/BrowserScreen';
import IdentitiesScreen from './screens/IdentitiesScreen';
import SettingsScreen from './screens/SettingsScreen';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <>
      <StatusBar style="auto" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={{
            tabBarActiveTintColor: '#4299E1',
            tabBarInactiveTintColor: '#A0AEC0',
            headerStyle: {
              backgroundColor: '#fff',
            },
            headerTintColor: '#2D3748',
            headerTitleStyle: {
              fontWeight: '600',
            },
          }}
        >
          <Tab.Screen
            name="Connect"
            component={HomeScreen}
            options={{
              title: 'Connect',
              tabBarLabel: 'Connect',
              headerTitle: 'Wormhole',
            }}
          />
          <Tab.Screen
            name="Browser"
            component={BrowserScreen}
            options={{
              title: 'Browser',
              tabBarLabel: 'Browser',
              headerTitle: 'WNS Browser',
            }}
          />
          <Tab.Screen
            name="Identities"
            component={IdentitiesScreen}
            options={{
              title: 'Identities',
              tabBarLabel: 'Identities',
              headerTitle: 'My Identities',
            }}
          />
          <Tab.Screen
            name="Settings"
            component={SettingsScreen}
            options={{
              title: 'Settings',
              tabBarLabel: 'Settings',
              headerTitle: 'Settings',
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </>
  );
}
